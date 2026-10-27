"""recon3d - a small, readable 3D-reconstruction-from-2D-images pipeline.

Stages (from the DIVAS seminar "3D reconstruction from 2D images"):
  1 image collection   -> images.py
  2 feature extraction -> features.py
  3 feature matching   -> matching.py
  4 structure from motion -> sfm.py
  5 dense point cloud  -> dense.py
  6 mesh reconstruction, 7 mesh refinement -> mesh.py
  8 mesh texturing     -> texture.py
"""
__version__ = "0.1.0"
