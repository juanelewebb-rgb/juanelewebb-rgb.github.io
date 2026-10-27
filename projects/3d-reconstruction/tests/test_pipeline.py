"""End-to-end check on synthetic photos with known camera positions.

Run:  pytest -q        (takes ~1 minute)
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
cv2 = pytest.importorskip("cv2")

from recon3d import features, images, matching, sfm  # noqa: E402
from recon3d.synthetic import make_dataset  # noqa: E402


def umeyama(src, dst):
    """Best similarity transform (scale, R, t) mapping src -> dst."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S, D = src - mu_s, dst - mu_d
    U, sig, Vt = np.linalg.svd(D.T @ S / len(src))
    d = np.sign(np.linalg.det(U @ Vt))
    E = np.diag([1, 1, d])
    R = U @ E @ Vt
    s = (sig * np.diag(E)).sum() / S.var(0).sum()
    return s, R, mu_d - s * R @ mu_s


@pytest.fixture(scope="module")
def reconstruction(tmp_path_factory):
    d = tmp_path_factory.mktemp("synthetic")
    make_dataset(d, n_images=24, size=(800, 600))
    paths = images.list_images(d)
    imgs = [images.load_image(p) for p in paths]
    h, w = imgs[0].shape[:2]
    f = 1.2 * max(w, h)
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
    feats = [features.extract(im, 4000) for im in imgs]
    m = matching.match_all(feats, window=4)
    rec = sfm.run_sfm(feats, m, K, verbose=False)
    return rec, np.load(d / "ground_truth_camera_centers.npy")


def test_all_cameras_registered(reconstruction):
    rec, truth = reconstruction
    assert len(rec.poses) >= 0.9 * len(truth)


def test_reprojection_error_is_subpixel(reconstruction):
    rec, _ = reconstruction
    assert rec.mean_reproj_error() < 1.0


def test_camera_orbit_matches_ground_truth(reconstruction):
    rec, truth = reconstruction
    ids = sorted(rec.poses)
    est = np.array([rec.centers()[i].ravel() for i in ids])
    s, R, t = umeyama(est, truth[ids])
    err = np.linalg.norm((s * (R @ est.T)).T + t - truth[ids], axis=1)
    # orbit radius is 3.6 units; require < 1.5% of that on average
    assert err.mean() < 0.015 * 3.6, f"mean camera position error {err.mean():.3f}"


def test_check_images_flags_too_few(tmp_path):
    make_dataset(tmp_path, n_images=5, size=(400, 300))
    assert any("at least 20" in w for w in images.check_images(tmp_path))


def test_mixed_portrait_and_landscape_photos(tmp_path):
    """Every 3rd photo is rotated 90 degrees (like a phone held sideways). Each photo then has its own image centre."""
    make_dataset(tmp_path, n_images=24, size=(800, 600))
    paths = images.list_images(tmp_path)
    imgs = [images.load_image(p) for p in paths]
    for k in range(0, len(imgs), 3):
        imgs[k] = np.ascontiguousarray(np.rot90(imgs[k]))
    f = 1.2 * 800
    Ks = [np.array([[f, 0, im.shape[1] / 2], [0, f, im.shape[0] / 2], [0, 0, 1.0]]) for im in imgs]
    assert len({im.shape[:2] for im in imgs}) == 2
    feats = [features.extract(im, 4000) for im in imgs]
    m = matching.match_all(feats, window=4)
    rec = sfm.run_sfm(feats, m, Ks, verbose=False)
    truth = np.load(tmp_path / "ground_truth_camera_centers.npy")
    assert len(rec.poses) >= 0.9 * len(truth)
    assert rec.mean_reproj_error() < 1.0
    ids = sorted(rec.poses)
    est = np.array([rec.centers()[i].ravel() for i in ids])
    s, R, t = umeyama(est, truth[ids])
    err = np.linalg.norm((s * (R @ est.T)).T + t - truth[ids], axis=1)
    # looser bound than the single-orientation test (measured about 2% of the orbit radius for this set)
    assert err.mean() < 0.03 * 3.6, f"mean camera position error {err.mean():.3f}"
