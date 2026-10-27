"""Stage 4 - Structure from Motion.

Recovers camera poses and a sparse 3D point cloud from matched features:
  1. link pairwise matches into *tracks* (the same physical point seen in many images)
  2. pick a good starting pair, get relative pose from the essential matrix, triangulate
  3. add the remaining images one by one with PnP (2D-3D), triangulate new points
  4. bundle adjustment: jointly refine poses + points to minimise reprojection error

Camera convention: x_cam = R @ X_world + t ; pixel = K @ x_cam.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix


# ---------------------------------------------------------------- tracks
def build_tracks(matches: dict, n_images: int, feats) -> list[dict[int, int]]:
    """Union-find over (image, keypoint) nodes. Returns list of {image: keypoint_idx}."""
    offset = np.cumsum([0] + [len(f.xy) for f in feats])
    parent = np.arange(offset[-1])

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for (i, j), (ia, ib) in matches.items():
        for a, b in zip(ia + offset[i], ib + offset[j]):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

    groups: dict[int, list[int]] = {}
    img_of = np.repeat(np.arange(n_images), [len(f.xy) for f in feats])
    touched = set()
    for (i, j), (ia, ib) in matches.items():
        touched.update((ia + offset[i]).tolist())
        touched.update((ib + offset[j]).tolist())
    for node in touched:
        groups.setdefault(find(node), []).append(node)

    tracks = []
    for nodes in groups.values():
        imgs = img_of[nodes]
        if len(set(imgs.tolist())) != len(nodes):   # same image twice -> ambiguous, drop
            continue
        tracks.append({int(img_of[n]): int(n - offset[img_of[n]]) for n in nodes})
    return tracks


# ---------------------------------------------------------------- geometry helpers
def projection(K, R, t):
    return K @ np.hstack([R, t.reshape(3, 1)])


def triangulate_track(obs_xy, Ps):
    """Linear (DLT) multi-view triangulation. obs_xy (n,2), Ps list of 3x4."""
    A = []
    for (x, y), P in zip(obs_xy, Ps):
        A.append(x * P[2] - P[0])
        A.append(y * P[2] - P[1])
    _, _, vt = np.linalg.svd(np.array(A))
    X = vt[-1]
    return X[:3] / X[3] if abs(X[3]) > 1e-12 else None


def reproj_error(K, R, t, X, xy):
    c = R @ X + np.asarray(t).ravel()
    if c[2] <= 0:
        return np.inf
    p = K @ c
    return float(np.linalg.norm(p[:2] / p[2] - xy))


def max_ray_angle_deg(X, centers):
    rays = X[None] - np.array(centers)
    rays /= np.linalg.norm(rays, axis=1, keepdims=True)
    cosmin = np.clip((rays @ rays.T).min(), -1, 1)
    return float(np.degrees(np.arccos(cosmin)))


# ---------------------------------------------------------------- reconstruction state
@dataclass
class Reconstruction:
    K: object                                      # one 3x3 matrix for all photos, or a list with one per photo
    feats: list
    tracks: list
    poses: dict = field(default_factory=dict)      # image idx -> (R, t)
    points: dict = field(default_factory=dict)     # track idx -> xyz

    def __post_init__(self):
        # Each photo gets its own K: same focal length, but the image centre depends on the photo's size,
        # so a mix of portrait and landscape photos works.
        self.Ks = [self.K] * len(self.feats) if np.ndim(self.K) == 2 else [np.asarray(k, float) for k in self.K]
        self.K = self.Ks[0]

    def centers(self):
        return {i: (-R.T @ t) for i, (R, t) in self.poses.items()}

    def point_array(self):
        ids = sorted(self.points)
        return ids, np.array([self.points[i] for i in ids]).reshape(-1, 3)

    # -- triangulate every track that is seen by >=2 registered images and not yet a point
    def triangulate_new(self, max_err=3.0, min_angle=1.5):
        added = 0
        for tid, tr in enumerate(self.tracks):
            if tid in self.points:
                continue
            reg = [i for i in tr if i in self.poses]
            if len(reg) < 2:
                continue
            xy = [self.feats[i].xy[tr[i]] for i in reg]
            Ps = [projection(self.Ks[i], *self.poses[i]) for i in reg]
            X = triangulate_track(xy, Ps)
            if X is None or not np.all(np.isfinite(X)):
                continue
            errs = [reproj_error(self.Ks[i], *self.poses[i], X, p) for i, p in zip(reg, xy)]
            if max(errs) > max_err:
                continue
            ctr = [(-self.poses[i][0].T @ self.poses[i][1]).ravel() for i in reg]
            if max_ray_angle_deg(X, ctr) < min_angle:
                continue
            self.points[tid] = X
            added += 1
        return added

    # -- drop points with big reprojection error after refinement
    def prune(self, max_err=4.0):
        bad = []
        for tid, X in self.points.items():
            for i, k in self.tracks[tid].items():
                if i in self.poses:
                    if reproj_error(self.Ks[i], *self.poses[i], X, self.feats[i].xy[k]) > max_err:
                        bad.append(tid)
                        break
        for tid in bad:
            del self.points[tid]
        return len(bad)

    # -- bundle adjustment
    def bundle_adjust(self, max_nfev=30, verbose=False):
        cams = sorted(self.poses)
        cam_idx = {c: n for n, c in enumerate(cams)}
        pids = sorted(self.points)
        pt_idx = {p: n for n, p in enumerate(pids)}
        obs = []   # (cam, pt, x, y)
        for tid in pids:
            for i, k in self.tracks[tid].items():
                if i in cam_idx:
                    obs.append((cam_idx[i], pt_idx[tid], *self.feats[i].xy[k]))
        if len(obs) < 20:
            return
        obs = np.array(obs)
        ci, pi, uv = obs[:, 0].astype(int), obs[:, 1].astype(int), obs[:, 2:4]
        rv0 = np.array([cv2.Rodrigues(self.poses[c][0])[0].ravel() for c in cams])
        t0 = np.array([self.poses[c][1].ravel() for c in cams])
        X0 = np.array([self.points[p] for p in pids])
        x0 = np.hstack([rv0.ravel(), t0.ravel(), X0.ravel()])
        nc, npts = len(cams), len(pids)
        fx = np.array([self.Ks[c][0, 0] for c in cams])
        fy = np.array([self.Ks[c][1, 1] for c in cams])
        cx = np.array([self.Ks[c][0, 2] for c in cams])
        cy = np.array([self.Ks[c][1, 2] for c in cams])

        def project(x):
            rv = x[:nc * 3].reshape(nc, 3)
            t = x[nc * 3:nc * 6].reshape(nc, 3)
            X = x[nc * 6:].reshape(npts, 3)
            # Rodrigues, vectorised
            th = np.linalg.norm(rv, axis=1, keepdims=True) + 1e-12
            k = rv / th
            v = X[pi]
            kk = k[ci]
            tt = th[ci]
            rot = (v * np.cos(tt) + np.cross(kk, v) * np.sin(tt)
                   + kk * (kk * v).sum(1, keepdims=True) * (1 - np.cos(tt)))
            c = rot + t[ci]
            z = np.where(np.abs(c[:, 2:3]) < 1e-9, 1e-9, c[:, 2:3])
            return np.hstack([(fx[ci] * c[:, 0] / z[:, 0] + cx[ci])[:, None], (fy[ci] * c[:, 1] / z[:, 0] + cy[ci])[:, None]])

        def resid(x):
            return (project(x) - uv).ravel()

        m = len(obs) * 2
        S = lil_matrix((m, len(x0)), dtype=int)
        rows = np.arange(len(obs))
        for s in range(3):
            S[2 * rows, ci * 3 + s] = 1
            S[2 * rows + 1, ci * 3 + s] = 1
            S[2 * rows, nc * 3 + ci * 3 + s] = 1
            S[2 * rows + 1, nc * 3 + ci * 3 + s] = 1
            S[2 * rows, nc * 6 + pi * 3 + s] = 1
            S[2 * rows + 1, nc * 6 + pi * 3 + s] = 1
        # gauge freedom: keep the first camera fixed by heavily weighting it via bounds
        lo, hi = np.full(len(x0), -np.inf), np.full(len(x0), np.inf)
        eps = 1e-9
        lo[0:3], hi[0:3] = x0[0:3] - eps, x0[0:3] + eps
        lo[nc * 3:nc * 3 + 3], hi[nc * 3:nc * 3 + 3] = x0[nc * 3:nc * 3 + 3] - eps, x0[nc * 3:nc * 3 + 3] + eps
        res = least_squares(resid, x0, jac_sparsity=S, bounds=(lo, hi), loss="huber", f_scale=2.0,
                            x_scale="jac", max_nfev=max_nfev, verbose=2 if verbose else 0)
        rv = res.x[:nc * 3].reshape(nc, 3)
        t = res.x[nc * 3:nc * 6].reshape(nc, 3)
        X = res.x[nc * 6:].reshape(npts, 3)
        for n, c in enumerate(cams):
            self.poses[c] = (cv2.Rodrigues(rv[n])[0], t[n].reshape(3, 1))
        for n, p in enumerate(pids):
            self.points[p] = X[n]

    def mean_reproj_error(self):
        errs = []
        for tid, X in self.points.items():
            for i, k in self.tracks[tid].items():
                if i in self.poses:
                    errs.append(reproj_error(self.Ks[i], *self.poses[i], X, self.feats[i].xy[k]))
        return float(np.mean(errs)) if errs else float("nan")


# ---------------------------------------------------------------- incremental SfM
def _initial_pair(rec: Reconstruction, matches):
    """Choose the pair with many inliers AND a real baseline (not a pure rotation / planar scene)."""
    ranked = sorted(matches.items(), key=lambda kv: -len(kv[1][0]))[:30]

    def normalise(K, p):
        return (p - K[:2, 2]) / K[0, 0]
    best = None
    for (i, j), (ia, ib) in ranked:
        pa, pb = rec.feats[i].xy[ia], rec.feats[j].xy[ib]
        na, nb = normalise(rec.Ks[i], pa), normalise(rec.Ks[j], pb)
        E, mask = cv2.findEssentialMat(na, nb, np.eye(3), cv2.RANSAC, 0.999, 1.0 / rec.Ks[i][0, 0])
        if E is None or E.shape != (3, 3):
            continue
        n, R, t, _ = cv2.recoverPose(E, na, nb, np.eye(3), mask=mask.copy())
        if n < 30:
            continue
        H, hmask = cv2.findHomography(pa, pb, cv2.RANSAC, 3.0)
        h_ratio = hmask.sum() / len(pa) if hmask is not None else 0
        in_ratio = n / len(pa)
        angle_score = n * (1 - h_ratio)
        if best is None or angle_score > best[0]:
            best = (angle_score, i, j, R, t)
    if best is None:
        raise RuntimeError("Could not find a good initial image pair - are the photos taken from different positions?")
    return best[1:]



def _register_image(rec, matches, c, obj, img):
    """Place image c using 2D-3D matches (PnP).

    Plain PnP has a mirror ambiguity when most points lie on one plane (e.g. a table/floor):
    it can return a camera *below* the plane that still fits the floor points. To avoid that we
    also try a pose seeded from the best-matching registered neighbour, keep whichever explains
    more points, and reject poses that look away from that neighbour.
    """
    K = rec.Ks[c]

    def count_inliers(rv, tv):
        proj, _ = cv2.projectPoints(obj, rv, tv, K, None)
        return int((np.linalg.norm(proj.reshape(-1, 2) - img, axis=1) < 4.0).sum())

    cands = []
    ok, rv, tv, inl = cv2.solvePnPRansac(obj, img, K, None, reprojectionError=4.0,
                                         iterationsCount=500, flags=cv2.SOLVEPNP_EPNP)
    if ok and inl is not None and len(inl) >= 12:
        rv, tv = cv2.solvePnPRefineLM(obj[inl.ravel()], img[inl.ravel()], K, None, rv, tv)
        cands.append((rv, tv))
    # neighbour = registered image sharing the most verified matches with c
    nb = max((j for j in rec.poses), key=lambda j: len(matches.get((min(c, j), max(c, j)), ([],))[0]), default=None)
    if nb is not None:
        Rn, tn = rec.poses[nb]
        rv0, _ = cv2.Rodrigues(Rn)
        ok2, rv2, tv2 = cv2.solvePnP(obj, img, K, None, rv0.copy(), tn.copy(), useExtrinsicGuess=True,
                                     flags=cv2.SOLVEPNP_ITERATIVE)
        if ok2:
            cands.append((rv2, tv2))
    best, best_n = None, 0
    for rv, tv in cands:
        n = count_inliers(rv, tv)
        if nb is not None:                      # optical axis must roughly agree with the neighbour's
            ax_new = cv2.Rodrigues(rv)[0][2]
            ax_nb = rec.poses[nb][0][2]
            if float(ax_new @ ax_nb) < np.cos(np.radians(75)):
                continue
        if n > best_n:
            best, best_n = (rv, tv), n
    if best is None or best_n < 12:
        return None, 0
    return best, best_n


def run_sfm(feats, matches, K, verbose=True) -> Reconstruction:
    """K: one 3x3 camera matrix, or a list with one per photo (needed when photo sizes/orientations differ)."""
    tracks = build_tracks(matches, len(feats), feats)
    rec = Reconstruction(K=K, feats=feats, tracks=tracks)
    if verbose:
        print(f"  {len(tracks)} tracks")
    i, j, R, t = _initial_pair(rec, matches)
    rec.poses[i] = (np.eye(3), np.zeros((3, 1)))
    rec.poses[j] = (R, t.reshape(3, 1))
    n = rec.triangulate_new(max_err=2.0, min_angle=1.0)
    if verbose:
        print(f"  initial pair ({i},{j}) -> {n} points")
    rec.bundle_adjust(max_nfev=15)

    remaining = set(range(len(feats))) - set(rec.poses)
    retried = False
    while True:
        if not remaining:
            # one more attempt for photos that failed earlier - more points exist by now
            late = set(range(len(feats))) - set(rec.poses)
            if retried or not late:
                break
            retried, remaining = True, late
        # image that sees the most already-triangulated points
        scores = {}
        for c in remaining:
            scores[c] = sum(1 for tid in rec.points if c in tracks[tid])
        c = max(scores, key=scores.get)
        if scores[c] < 12:
            break
        tids = [tid for tid in rec.points if c in tracks[tid]]
        obj = np.array([rec.points[tid] for tid in tids], np.float64)
        img = np.array([feats[c].xy[tracks[tid][c]] for tid in tids], np.float64)
        pose, n_inl = _register_image(rec, matches, c, obj, img)
        remaining.discard(c)
        if pose is None:
            if verbose:
                print(f"  image {c}: could not be placed reliably - skipped")
            continue
        rvec, tvec = pose
        inl = np.arange(n_inl)
        rec.poses[c] = (cv2.Rodrigues(rvec)[0], tvec.reshape(3, 1))
        added = rec.triangulate_new()
        if verbose:
            print(f"  registered image {c:3d} ({len(inl)} PnP inliers, +{added} points, "
                  f"{len(rec.poses)}/{len(feats)} cams)")
        if len(rec.poses) % 4 == 0:
            rec.bundle_adjust(max_nfev=10)
            rec.prune(4.0)

    rec.bundle_adjust(max_nfev=40)
    rec.prune(3.0)
    rec.triangulate_new()
    rec.bundle_adjust(max_nfev=20)
    rec.prune(2.5)
    if verbose:
        print(f"  final: {len(rec.poses)} cameras, {len(rec.points)} points, "
              f"mean reprojection error {rec.mean_reproj_error():.2f}px")
    return rec
