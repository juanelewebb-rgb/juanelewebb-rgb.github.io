"""Generate a fake photo set (a textured cube on a textured floor, photographed on an orbit).

Lets you test that the whole pipeline works *before* you spend time photographing a real plant,
and gives you ground truth to compare against.   python -m recon3d synthetic data/synthetic
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _texture(seed, size=512):
    rng = np.random.default_rng(seed)
    t = np.zeros((size, size, 3), np.float32)
    for s, wgt in ((8, 1.0), (32, 0.7), (128, 0.5)):
        small = rng.random((size // s, size // s, 3)).astype(np.float32)
        t += wgt * cv2.resize(small, (size, size), interpolation=cv2.INTER_CUBIC)
    t = (t - t.min()) / (t.max() - t.min())
    img = (t * 255).astype(np.uint8)
    for _ in range(40):                                   # random blobs/rectangles = extra corners
        c = tuple(int(v) for v in rng.integers(0, 255, 3))
        x, y = rng.integers(0, size - 60, 2)
        if rng.random() < 0.5:
            cv2.rectangle(img, (x, y), (x + int(rng.integers(15, 60)), y + int(rng.integers(15, 60))), c, -1)
        else:
            cv2.circle(img, (x, y), int(rng.integers(8, 30)), c, -1)
    return img


def make_dataset(out_dir, n_images=36, size=(1000, 750), seed=0):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    W, H = size
    f = 1.2 * max(W, H)
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], float)
    s = 0.5
    # cube faces (corner order matches texture corner order), floor at y = +s  (y points down)
    faces = {
        "front":  [(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s)],
        "back":   [(s, -s, s), (-s, -s, s), (-s, s, s), (s, s, s)],
        "left":   [(-s, -s, s), (-s, -s, -s), (-s, s, -s), (-s, s, s)],
        "right":  [(s, -s, -s), (s, -s, s), (s, s, s), (s, s, -s)],
        "top":    [(-s, -s, s), (s, -s, s), (s, -s, -s), (-s, -s, -s)],
    }
    floor = [(-3, s, 3), (3, s, 3), (3, s, -3), (-3, s, -3)]
    tex = {k: _texture(seed + n) for n, k in enumerate(list(faces) + ["floor"])}
    tc = np.float32([[0, 0], [511, 0], [511, 511], [0, 511]])
    rng = np.random.default_rng(seed)

    truth = []
    for n in range(n_images):
        th = 2 * np.pi * n / n_images
        elev = np.radians(18 + 14 * np.sin(3 * th))
        r = 3.6
        eye = np.array([r * np.cos(elev) * np.cos(th), -r * np.sin(elev), r * np.cos(elev) * np.sin(th)])
        truth.append(eye)
        z = -eye / np.linalg.norm(eye)                         # forward
        x = np.cross([0, 1.0, 0], z)
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        R = np.stack([x, y, z])                                # world -> cam
        t = -R @ eye
        canvas = np.full((H, W, 3), (200, 180, 160), np.uint8)

        def project(P):
            c = (R @ np.array(P, float).T).T + t
            p = (K @ c.T).T
            return (p[:, :2] / p[:, 2:3]).astype(np.float32), c

        def draw(name, quad, cull=True):
            pts, cam = project(quad)
            if (cam[:, 2] < 0.2).any():
                return
            nrm = np.cross(np.array(quad[1]) - quad[0], np.array(quad[2]) - quad[1])
            if cull and nrm @ (eye - np.array(quad[0])) <= 0:
                return
            Hm = cv2.getPerspectiveTransform(tc, pts)
            warped = cv2.warpPerspective(tex[name], Hm, (W, H), flags=cv2.INTER_LINEAR)
            mask = cv2.warpPerspective(np.full((512, 512), 255, np.uint8), Hm, (W, H), flags=cv2.INTER_NEAREST)
            canvas[mask > 0] = warped[mask > 0]

        draw("floor", floor, cull=False)
        for name in sorted(faces, key=lambda k: -np.linalg.norm(eye - np.mean(faces[k], axis=0))):
            draw(name, faces[name])
        canvas = cv2.GaussianBlur(canvas, (3, 3), 0.6)
        noise = rng.normal(0, 2.0, canvas.shape)
        canvas = np.clip(canvas + noise, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out / f"synthetic_{n:03d}.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
    np.save(out / "ground_truth_camera_centers.npy", np.array(truth))
    return out
