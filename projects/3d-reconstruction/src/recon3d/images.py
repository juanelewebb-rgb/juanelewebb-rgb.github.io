"""Stage 1 - image collection: load photos and check them against the capture rules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

EXTS = {".jpg", ".jpeg", ".png"}
MIN_IMAGES = 20          # assignment: "at least 20 images"
BLUR_RATIO = 0.5         # flag photos whose sharpness is < 50% of the set median


def list_images(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)


def load_image(path: Path, max_dim: int = 1600) -> np.ndarray:
    """Load BGR image, downscaled so the longest side is <= max_dim."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(f"could not read {path}")
    h, w = img.shape[:2]
    s = max_dim / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def focal_pixels(path: Path, width: int, height: int) -> float:
    """Focal length in pixels for an image of the given (possibly resized) size.

    Uses EXIF 35mm-equivalent focal length when present, otherwise falls back
    to 1.2 * longest side (a typical phone-camera value).
    """
    try:
        exif = Image.open(path).getexif()
        sub = exif.get_ifd(0x8769)
        tags = {TAGS.get(k, k): v for k, v in {**dict(exif), **dict(sub)}.items()}
        f35 = tags.get("FocalLengthIn35mmFilm")
        if f35:
            return float(f35) / 36.0 * max(width, height)
    except Exception:
        pass
    return 1.2 * max(width, height)


def camera_matrices(paths, imgs) -> list:
    """One 3x3 camera matrix per photo (focal length from EXIF, image centre from that photo's own size).

    Per-photo matrices let a set that mixes portrait and landscape shots work correctly.
    """
    Ks = []
    for p, im in zip(paths, imgs):
        h, w = im.shape[:2]
        f = focal_pixels(p, w, h)
        Ks.append(np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]]))
    return Ks


@dataclass
class ImageReport:
    name: str
    width: int
    height: int
    sharpness: float



def check_images(folder: str | Path) -> list[str]:
    """Return human-readable warnings based on the professor's capture rules."""
    paths = list_images(folder)
    warnings: list[str] = []
    if len(paths) < MIN_IMAGES:
        warnings.append(f"Only {len(paths)} images found - the assignment asks for at least {MIN_IMAGES} "
                        f"(more is better; Polycam accepts 20-150).")
    reports = []
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            warnings.append(f"{p.name}: unreadable file")
            continue
        h, w = img.shape
        reports.append(ImageReport(p.name, w, h, float(cv2.Laplacian(img, cv2.CV_64F).var())))
    if reports:
        med = float(np.median([r.sharpness for r in reports]))
        for r in reports:
            if r.sharpness < BLUR_RATIO * med:
                warnings.append(f"{r.name}: much blurrier than your other photos "
                                f"(sharpness {r.sharpness:.0f} vs median {med:.0f}) - retake it")
    sizes = {(r.width, r.height) for r in reports}
    if len(sizes) > 1:
        if len({tuple(sorted(sz)) for sz in sizes}) == 1:
            warnings.append("Photos are a mix of portrait and landscape - that is handled automatically, "
                            "but keep the same zoom and lens for every shot.")
        else:
            warnings.append(f"Images have {len(sizes)} different sizes {sorted(sizes)} - use one camera/zoom setting.")
    return warnings
