"""Glue: run every stage, save every intermediate result so you can inspect each step."""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d

from . import dense, features, images, matching, mesh, render, sfm, texture


def _step(msg):
    print(f"\n== {msg}")
    return time.time()


def run(image_dir, out_dir, max_dim=1600, window=None, n_features=6000, poisson_depth=8,
        make_video=True, skip_dense=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t0 = _step("1/8 image collection")
    paths = images.list_images(image_dir)
    for w in images.check_images(image_dir):
        print("  WARNING:", w)
    imgs = [images.load_image(p, max_dim) for p in paths]
    K = images.camera_matrices(paths, imgs)           # one per photo (portrait/landscape mixes are fine)
    sizes = sorted({im.shape[1::-1] for im in imgs})
    print(f"  {len(imgs)} images, sizes {sizes}, focal ~{K[0][0, 0]:.0f}px")

    _step("2/8 feature extraction (RootSIFT)")
    feats = [features.extract(im, n_features) for im in imgs]
    print(f"  avg {np.mean([len(x.xy) for x in feats]):.0f} keypoints/image")
    (out / "debug").mkdir(exist_ok=True)
    cv2.imwrite(str(out / "debug" / "keypoints_0.jpg"), features.draw_keypoints(imgs[0], feats[0]))

    _step("3/8 feature matching + geometric verification")
    m = matching.match_all(feats, window=window)
    print(f"  {len(m)} verified image pairs")
    if m:
        (i, j), (ia, ib) = max(m.items(), key=lambda kv: len(kv[1][0]))
        cv2.imwrite(str(out / "debug" / "matches_best_pair.jpg"),
                    matching.draw_matches(imgs[i], imgs[j], feats[i], feats[j], ia, ib))
    if len(m) < 3:
        raise SystemExit("Too few matching image pairs. Check overlap (70-80%) and that photos are sharp.")

    _step("4/8 structure from motion (camera poses + sparse cloud)")
    rec = sfm.run_sfm(feats, m, K)
    ids, sparse = rec.point_array()
    cols = dense._sparse_colors(rec, imgs, ids)
    sp = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(sparse))
    sp.colors = o3d.utility.Vector3dVector(cols)
    o3d.io.write_point_cloud(str(out / "sparse.ply"), sp)
    np.save(out / "camera_centers.npy", np.array([c.ravel() for c in rec.centers().values()]))

    _step("5/8 dense point cloud")
    if skip_dense:
        pcd = sp
    else:
        pcd = dense.dense_cloud(rec, imgs)
    print(f"  {len(pcd.points)} points")
    o3d.io.write_point_cloud(str(out / "dense.ply"), pcd)

    _step("6/8 mesh reconstruction (Poisson)")
    centers = list(rec.centers().values())
    raw = mesh.reconstruct_mesh(pcd, centers, depth=poisson_depth)
    print(f"  {len(raw.vertices)} vertices / {len(raw.triangles)} triangles")

    _step("7/8 mesh refinement")
    ref = mesh.refine_mesh(raw)
    print(f"  {len(ref.vertices)} vertices / {len(ref.triangles)} triangles")

    _step("8/8 mesh texturing (photo colours)")
    tex = texture.colorize_mesh(ref, rec, imgs)
    o3d.io.write_triangle_mesh(str(out / "model.ply"), tex)
    o3d.io.write_triangle_mesh(str(out / "model.obj"), tex)
    print(f"  wrote {out/'model.ply'} and model.obj")

    if make_video:
        _step("turntable video")
        render.turntable(tex, str(out / "model_turntable.mp4"))
        print(f"  wrote {out/'model_turntable.mp4'}")
    return rec, tex
