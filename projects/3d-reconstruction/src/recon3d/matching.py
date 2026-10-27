"""Stage 3 - feature matching between images (+ geometric verification)."""
from __future__ import annotations

import cv2
import numpy as np

from .features import Features


def match_pair(fa: Features, fb: Features, ratio: float = 0.8):
    """Lowe ratio-test matching. Returns (idx_a, idx_b) int arrays (mutual-consistent)."""
    if len(fa.xy) < 8 or len(fb.xy) < 8:
        return np.zeros(0, int), np.zeros(0, int)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    ab = bf.knnMatch(fa.desc, fb.desc, k=2)
    ba = bf.knnMatch(fb.desc, fa.desc, k=1)
    back = {m[0].queryIdx: m[0].trainIdx for m in ba if m}
    ia, ib = [], []
    for pair in ab:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance and back.get(m.trainIdx) == m.queryIdx:
            ia.append(m.queryIdx)
            ib.append(m.trainIdx)
    return np.array(ia, int), np.array(ib, int)


def verify_pair(fa: Features, fb: Features, ia, ib, thresh_px: float = 1.5):
    """Keep only matches consistent with one epipolar geometry (RANSAC fundamental matrix)."""
    if len(ia) < 15:
        return np.zeros(0, int), np.zeros(0, int), None
    pa, pb = fa.xy[ia], fb.xy[ib]
    F, mask = cv2.findFundamentalMat(pa, pb, cv2.FM_RANSAC, thresh_px, 0.999)
    if F is None or mask is None:
        return np.zeros(0, int), np.zeros(0, int), None
    mask = mask.ravel().astype(bool)
    return ia[mask], ib[mask], F


def match_all(feats: list[Features], window: int | None = None, min_inliers: int = 30):
    """Match every pair (or only pairs within `window` index distance, for ordered photo sets).

    Returns {(i, j): (idx_i, idx_j)} with i < j.
    """
    n = len(feats)
    out = {}
    for i in range(n):
        for j in range(i + 1, n):
            if window is not None and min(j - i, n - (j - i)) > window:
                continue
            ia, ib = match_pair(feats[i], feats[j])
            ia, ib, _ = verify_pair(feats[i], feats[j], ia, ib)
            if len(ia) >= min_inliers:
                out[(i, j)] = (ia, ib)
    return out


def draw_matches(img_a, img_b, fa, fb, ia, ib, max_lines: int = 150) -> np.ndarray:
    ha, wa = img_a.shape[:2]
    hb, wb = img_b.shape[:2]
    canvas = np.zeros((max(ha, hb), wa + wb, 3), np.uint8)
    canvas[:ha, :wa] = img_a
    canvas[:hb, wa:] = img_b
    rng = np.random.default_rng(0)
    for k in rng.permutation(len(ia))[:max_lines]:
        c = tuple(int(v) for v in rng.integers(60, 255, 3))
        p, q = fa.xy[ia[k]], fb.xy[ib[k]]
        cv2.line(canvas, (int(p[0]), int(p[1])), (int(q[0]) + wa, int(q[1])), c, 1, cv2.LINE_AA)
    return canvas
