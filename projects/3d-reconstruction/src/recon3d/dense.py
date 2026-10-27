"""Stage 5 - dense point cloud.

SfM gives a *sparse* cloud (only points that had matching features). To fill in surfaces we run
two-view stereo (semi-global block matching) between neighbouring cameras: rectify the pair so
matching pixels lie on the same row, compute a disparity map, then turn disparity into 3D.
Results from all pairs are merged and voxel-downsampled.
"""
from __future__ import annotations

import cv2
import numpy as np
import open3d as o3d


def _pairs(rec, n_per_cam=2, min_deg=3.0, max_deg=25.0):
    cen = rec.centers()
    ids = sorted(rec.poses)
    target = np.mean([cen[i].ravel() for i in ids], axis=0)
    pairs = set()
    for i in ids:
        ci = cen[i].ravel()
        cands = []
        for j in ids:
            if j == i:
                continue
            a, b = ci - target, cen[j].ravel() - target
            ang = np.degrees(np.arccos(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12), -1, 1)))
            if min_deg <= ang <= max_deg:
                cands.append((ang, j))
        for _, j in sorted(cands)[:n_per_cam]:
            pairs.add((min(i, j), max(i, j)))
    return sorted(pairs)


def stereo_pair(rec, imgs, i, j, scale=0.5, num_disp=192, block=5):
    """Dense depth from one camera pair. Returns world-space points + RGB colours."""
    if imgs[i].shape[:2] != imgs[j].shape[:2]:
        raise ValueError("photos have different sizes (portrait vs landscape) - cannot rectify this pair")

    def scaled(K):
        K = K.copy()
        K[:2] *= scale                               # work at reduced resolution (faster, smaller disparities)
        return K

    h, w = imgs[i].shape[:2]
    size = (int(w * scale), int(h * scale))

    def rectify(a, b):
        (Ra, ta), (Rb, tb) = rec.poses[a], rec.poses[b]
        R = Rb @ Ra.T
        T = tb - R @ ta
        return cv2.stereoRectify(scaled(rec.Ks[a]), None, scaled(rec.Ks[b]), None, size, R, T, alpha=1)

    R1, R2, P1, P2, Q, _, _ = rectify(i, j)
    if P2[0, 3] > 0:                                 # disparity would be negative -> swap the pair order
        i, j = j, i
        R1, R2, P1, P2, Q, _, _ = rectify(i, j)
    Ri, ti = rec.poses[i]
    small = [cv2.resize(imgs[i], size, interpolation=cv2.INTER_AREA),
             cv2.resize(imgs[j], size, interpolation=cv2.INTER_AREA)]
    m1 = cv2.initUndistortRectifyMap(scaled(rec.Ks[i]), None, R1, P1, size, cv2.CV_32FC1)
    m2 = cv2.initUndistortRectifyMap(scaled(rec.Ks[j]), None, R2, P2, size, cv2.CV_32FC1)
    ri = cv2.remap(small[0], *m1, cv2.INTER_LINEAR)
    rj = cv2.remap(small[1], *m2, cv2.INTER_LINEAR)
    gi, gj = cv2.cvtColor(ri, cv2.COLOR_BGR2GRAY), cv2.cvtColor(rj, cv2.COLOR_BGR2GRAY)
    sgbm = cv2.StereoSGBM_create(minDisparity=0, numDisparities=num_disp, blockSize=block,
                                 P1=8 * block * block, P2=32 * block * block, uniquenessRatio=10,
                                 speckleWindowSize=100, speckleRange=2, disp12MaxDiff=1,
                                 mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    disp = sgbm.compute(gi, gj).astype(np.float32) / 16.0
    valid = disp > 1.0
    # ignore the black borders that rectification leaves around the image ...
    ones = np.full(small[0].shape[:2], 255, np.uint8)
    inside = cv2.remap(ones, *m1, cv2.INTER_NEAREST) > 0
    inside = cv2.erode(inside.astype(np.uint8), np.ones((2 * block + 3,) * 2, np.uint8)) > 0
    # ... and flat, texture-less pixels (blank wall/table): stereo cannot match those reliably
    g = gi.astype(np.float32)
    var = cv2.boxFilter(g * g, -1, (7, 7)) - cv2.boxFilter(g, -1, (7, 7)) ** 2
    valid &= inside & (var > 25.0)
    xyz = cv2.reprojectImageTo3D(disp, Q)            # in the rectified frame of camera i
    valid &= np.isfinite(xyz).all(axis=2) & (xyz[..., 2] > 0)
    cols = ri[valid][:, ::-1] / 255.0                # BGR -> RGB
    pts_cam = xyz[valid] @ R1                        # undo rectifying rotation: cam = R1^T x
    pts_world = (Ri.T @ (pts_cam.T - ti)).T
    return pts_world, cols


def dense_cloud(rec, imgs, voxel=None, verbose=True) -> o3d.geometry.PointCloud:
    sparse_ids, sparse = rec.point_array()
    scene = np.percentile(np.linalg.norm(sparse - np.median(sparse, axis=0), axis=1), 90) if len(sparse) else 1.0
    all_p, all_c = [], []
    for i, j in _pairs(rec):
        try:
            p, c = stereo_pair(rec, imgs, i, j)
        except (cv2.error, ValueError) as e:
            if verbose:
                print(f"  pair ({i},{j}) skipped: {str(e).splitlines()[0][:80]}")
            continue
        # keep only points near the sparse reconstruction (rejects stereo garbage)
        keep = np.linalg.norm(p - np.median(sparse, axis=0), axis=1) < 3.0 * scene
        all_p.append(p[keep][::2])
        all_c.append(c[keep][::2])
        if verbose:
            print(f"  stereo pair ({i:2d},{j:2d}): {keep.sum()} points")
    pcd = o3d.geometry.PointCloud()
    if all_p:
        pcd.points = o3d.utility.Vector3dVector(np.vstack(all_p))
        pcd.colors = o3d.utility.Vector3dVector(np.vstack(all_c))
    # always include the SfM points so we never end up with an empty cloud
    sp = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(sparse))
    sp.colors = o3d.utility.Vector3dVector(_sparse_colors(rec, imgs, sparse_ids))
    voxel = voxel or scene / 150.0
    if len(pcd.points):
        # stereo garbage floats far from anything SfM saw: keep only points near the sparse structure
        near = np.asarray(pcd.compute_point_cloud_distance(sp)) < 0.25 * scene
        pcd = pcd.select_by_index(np.where(near)[0])
    pcd += sp
    pcd = pcd.voxel_down_sample(voxel)
    pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    return pcd


def _sparse_colors(rec, imgs, ids):
    cols = []
    for tid in ids:
        i, k = next(iter(rec.tracks[tid].items()))
        x, y = rec.feats[i].xy[k]
        h, w = imgs[i].shape[:2]
        b, g, r = imgs[i][min(h - 1, int(y)), min(w - 1, int(x))]
        cols.append((r / 255.0, g / 255.0, b / 255.0))
    return np.array(cols).reshape(-1, 3)
