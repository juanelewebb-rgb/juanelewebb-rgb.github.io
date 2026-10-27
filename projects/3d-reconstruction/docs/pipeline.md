# How the pipeline works

Mirrors the 8 steps in the seminar slides.

**1. Image collection** - photos are loaded, downscaled (default longest side 1600 px) and checked. The camera matrix is
`K = [[f,0,cx],[0,f,cy],[0,0,1]]` with `f` from EXIF (35 mm-equivalent focal length) or `1.2 x max(width, height)`.

**2. Feature extraction** - SIFT finds repeatable corner/blob "keypoints" and a 128-number descriptor for each.
We apply the RootSIFT trick (L1-normalise, square root), which improves matching for free.

**3. Feature matching** - for each image pair, find the nearest descriptor in the other image. The *ratio test*
(best match must be clearly better than second best) and a *mutual check* throw away ambiguous matches. The survivors are
then verified geometrically: a true correspondence must satisfy the epipolar constraint `x2^T F x1 = 0`; RANSAC fits `F`
and drops everything that disagrees (this is the epipolar geometry slide).

**4. Structure from Motion** -
* matches are chained into *tracks* (the same physical point seen in many photos) with union-find;
* the start pair is the verified pair with many inliers and a genuine baseline (not a pure rotation/plane);
  the essential matrix `E` gives relative rotation and translation direction;
* points are triangulated (the "two rays meet at X" slide, generalised to many views with the DLT);
* each remaining photo is placed with PnP (known 3D points <-> their 2D pixels). Plain PnP can return a mirror-image camera
  when most points lie on one plane, so the pose is also seeded from the best neighbouring camera and sanity-checked;
* **bundle adjustment** (`scipy.optimize.least_squares`, sparse Jacobian, Huber loss) jointly refines every camera and
  point to minimise reprojection error.

**5. Dense point cloud** - SfM only reconstructs points that had features. For the rest, neighbouring camera pairs are
*rectified* (virtually rotated so matching pixels share a row), semi-global block matching computes a disparity per pixel,
and `Z = f*B/disparity` converts that to depth. Points from all pairs are merged and voxel-filtered.

**6. Mesh reconstruction** - Poisson surface reconstruction fits a smooth watertight surface to the oriented points;
low-density vertices (surface Poisson invented far from data) are trimmed.

**7. Mesh refinement** - remove small disconnected pieces, degenerate triangles, decimate, Taubin-smooth.

**8. Mesh texturing** - each vertex takes the colour from the photos that see it most face-on.

Scale ambiguity: monocular SfM recovers shape only up to an unknown scale, so measurements need a reference object.
