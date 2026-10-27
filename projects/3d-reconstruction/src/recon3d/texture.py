"""Stage 8 - mesh texturing: give every vertex a colour from the photos.

For each vertex we pick the camera that looks at it most head-on (and where it projects
inside the image), then sample the pixel colour. Simple per-vertex colouring, no UV atlas.
"""
from __future__ import annotations

import numpy as np
import open3d as o3d


def colorize_mesh(mesh, rec, imgs, top_k: int = 3):
    mesh = o3d.geometry.TriangleMesh(mesh)
    mesh.compute_vertex_normals()
    V = np.asarray(mesh.vertices)
    N = np.asarray(mesh.vertex_normals)
    ids = sorted(rec.poses)
    score = np.full((len(ids), len(V)), -1.0)
    colors = np.zeros((len(ids), len(V), 3))
    for n, i in enumerate(ids):
        R, t = rec.poses[i]
        K = rec.Ks[i]
        cam = (R @ V.T + t).T
        center = (-R.T @ t).ravel()
        view = center - V
        view /= np.linalg.norm(view, axis=1, keepdims=True) + 1e-12
        facing = (N * view).sum(1)
        z = cam[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = K[0, 0] * cam[:, 0] / z + K[0, 2]
            v = K[1, 1] * cam[:, 1] / z + K[1, 2]
        h, w = imgs[i].shape[:2]
        ok = (z > 0) & (u >= 0) & (u < w - 1) & (v >= 0) & (v < h - 1) & (facing > 0.1)
        score[n, ok] = facing[ok]
        uu, vv = np.clip(u[ok].astype(int), 0, w - 1), np.clip(v[ok].astype(int), 0, h - 1)
        colors[n, ok] = imgs[i][vv, uu][:, ::-1] / 255.0
    order = np.argsort(-score, axis=0)[:top_k]                       # best k cameras per vertex
    best = np.take_along_axis(score, order, 0)
    wts = np.clip(best, 0, None)
    cols = np.take_along_axis(colors, order[..., None], 0)
    final = (cols * wts[..., None]).sum(0) / (wts.sum(0)[:, None] + 1e-9)
    nocam = wts.sum(0) == 0
    final[nocam] = 0.6
    mesh.vertex_colors = o3d.utility.Vector3dVector(final)
    return mesh
