"""Turntable video of the result (the assignment's deliverable is a video of your model).

Pure numpy/OpenCV point-splat renderer, so it works on any laptop and over SSH (no OpenGL window needed).
"""
from __future__ import annotations

import os
import shutil
import subprocess

import cv2
import numpy as np
import open3d as o3d


def _ffmpeg_exe():
    """ffmpeg from the imageio-ffmpeg pip package (no apt needed), else one on PATH, else None."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _to_h264(path: str) -> bool:
    """OpenCV writes old MPEG-4 video that VS Code / browsers / many players can't play.
    Re-encode to H.264 (plays everywhere, and is what you want to upload)."""
    exe = _ffmpeg_exe()
    if not exe:
        return False
    tmp = path + ".h264.mp4"
    r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "20", "-movflags", "+faststart", tmp], capture_output=True)
    if r.returncode == 0 and os.path.exists(tmp):
        os.replace(tmp, path)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def _geometry_points(geom):
    if isinstance(geom, o3d.geometry.TriangleMesh):
        V = np.asarray(geom.vertices)
        C = np.asarray(geom.vertex_colors) if geom.has_vertex_colors() else np.full((len(V), 3), 0.7)
        # add points on triangles so the surface looks solid
        T = np.asarray(geom.triangles)
        if len(T):
            rng = np.random.default_rng(0)
            n = min(400000, len(T) * 6)
            tri = T[rng.integers(0, len(T), n)]
            w = rng.dirichlet([1, 1, 1], n)
            P = (V[tri] * w[..., None]).sum(1)
            Cc = (C[tri] * w[..., None]).sum(1)
            return np.vstack([V, P]), np.vstack([C, Cc])
        return V, C
    P = np.asarray(geom.points)
    C = np.asarray(geom.colors) if geom.has_colors() else np.full((len(P), 3), 0.7)
    return P, C


def turntable(geom, out_path: str, up=(0.0, -1.0, 0.0), seconds=8, fps=24, size=(960, 720), elev_deg=15):
    P, C = _geometry_points(geom)
    ctr = np.median(P, axis=0)
    P = P - ctr
    rad = np.percentile(np.linalg.norm(P, axis=1), 98) + 1e-9
    up = np.asarray(up, float)
    up /= np.linalg.norm(up)
    a = np.cross(up, [1, 0, 0] if abs(up[0]) < 0.9 else [0, 0, 1])
    a /= np.linalg.norm(a)
    b = np.cross(up, a)                      # horizontal basis (a, b), vertical = up
    W, H = size
    f = 1.6 * min(W, H)
    vw = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    el = np.radians(elev_deg)
    for fr in range(int(seconds * fps)):
        th = 2 * np.pi * fr / (seconds * fps)
        right = np.cos(th) * a + np.sin(th) * b
        fwd = -np.sin(th) * a + np.cos(th) * b
        x, y, z = P @ right, P @ up, P @ fwd
        # tilt camera by elev
        y2 = y * np.cos(el) - z * np.sin(el)
        z2 = y * np.sin(el) + z * np.cos(el) + 3.2 * rad
        ok = z2 > 0.1 * rad
        u = (f * x[ok] / z2[ok] + W / 2).astype(int)
        v = (H / 2 - f * y2[ok] / z2[ok]).astype(int)
        inb = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        u, v, zz, cc = u[inb], v[inb], z2[ok][inb], C[ok][inb]
        order = np.argsort(-zz)                 # far -> near, near wins
        img = np.full((H, W, 3), 255, np.uint8)
        col = (cc[order][:, ::-1] * 255).astype(np.uint8)
        r = max(1, int(round(W / 400)))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                uu, vv = np.clip(u[order] + dx, 0, W - 1), np.clip(v[order] + dy, 0, H - 1)
                img[vv, uu] = col
        vw.write(img)
    vw.release()
    if not _to_h264(out_path):
        print("  (note: could not convert video to H.264 - run `pip install imageio-ffmpeg`; "
              "the file may not play in VS Code but opens in VLC/Windows players)")
