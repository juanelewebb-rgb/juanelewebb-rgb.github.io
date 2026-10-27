"""Stages 6 + 7 - mesh reconstruction (Poisson) and mesh refinement."""
from __future__ import annotations

import numpy as np
import open3d as o3d


def reconstruct_mesh(pcd: o3d.geometry.PointCloud, camera_centers, depth: int = 9) -> o3d.geometry.TriangleMesh:
    """Point cloud -> watertight surface using Poisson surface reconstruction."""
    pcd = o3d.geometry.PointCloud(pcd)
    extent = np.linalg.norm(pcd.get_max_bound() - pcd.get_min_bound())
    pcd.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=extent * 0.02, max_nn=40))
    # orient normals toward the cameras that saw the points (outward-facing surface)
    mean_cam = np.mean(np.array(camera_centers).reshape(-1, 3), axis=0)
    pcd.orient_normals_towards_camera_location(mean_cam)
    mesh, density = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth)
    d = np.asarray(density)
    mesh.remove_vertices_by_mask(d < np.quantile(d, 0.08))   # trim the "bubbles" Poisson invents
    return mesh


def refine_mesh(mesh: o3d.geometry.TriangleMesh, smooth_iters: int = 10, max_triangles: int = 300_000) -> o3d.geometry.TriangleMesh:
    """Clean up: drop tiny floating pieces, remove degenerate faces, simplify, smooth gently."""
    mesh = o3d.geometry.TriangleMesh(mesh)
    clusters, counts, _ = mesh.cluster_connected_triangles()
    clusters, counts = np.asarray(clusters), np.asarray(counts)
    if len(counts):
        mesh.remove_triangles_by_mask(counts[clusters] < max(100, counts.max() * 0.05))
    mesh.remove_unreferenced_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    if len(mesh.triangles) > max_triangles:
        mesh = mesh.simplify_quadric_decimation(max_triangles)
    mesh = mesh.filter_smooth_taubin(number_of_iterations=smooth_iters)   # smooths without shrinking
    mesh.compute_vertex_normals()
    return mesh
