"""Stage 2 - feature extraction: find keypoints + descriptors (SIFT)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Features:
    xy: np.ndarray      # (N,2) float32 pixel coordinates
    desc: np.ndarray    # (N,128) float32 RootSIFT descriptors


def extract(img_bgr: np.ndarray, n_features: int = 6000) -> Features:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=n_features, contrastThreshold=0.02)
    kps, desc = sift.detectAndCompute(gray, None)
    if desc is None or len(kps) == 0:
        return Features(np.zeros((0, 2), np.float32), np.zeros((0, 128), np.float32))
    # RootSIFT: L1-normalise then sqrt - matches noticeably better than raw SIFT
    desc = desc / (desc.sum(axis=1, keepdims=True) + 1e-7)
    desc = np.sqrt(desc).astype(np.float32)
    xy = np.array([k.pt for k in kps], np.float32)
    return Features(xy, desc)


def draw_keypoints(img_bgr: np.ndarray, feats: Features, max_pts: int = 800) -> np.ndarray:
    out = img_bgr.copy()
    for x, y in feats.xy[:max_pts]:
        cv2.circle(out, (int(x), int(y)), 3, (0, 255, 0), 1, cv2.LINE_AA)
    return out
