"""Pull colored curves out of a plot image by color.

How it works, for one curve:
  1. Every pixel is labeled with the nearest reference color (the legend
     colors, plus white). A pixel only counts if it is close to that color.
  2. Areas that are not data (legend, axis frame, tick marks, labels) are
     masked out.
  3. In each pixel column, the matching pixels form one or more short runs.
     The run closest to the previous column's position is kept, so the trace
     follows the curve instead of jumping to noise.
  4. Columns where the curve is hidden (another curve drawn on top of it)
     are filled by straight-line interpolation and flagged in the output.
  5. Pixel positions are converted to data units with the axis calibration
     (two known ticks per axis), then resampled every `step` nm.

The output is a reading of a published figure, not the original data. Expect
errors of about a line width (here roughly +/-2 nm and +/-0.01 in y).
"""
import csv
from pathlib import Path

import numpy as np
from PIL import Image

WHITE = (255, 255, 255)


def classify(img, refs, max_dist):
    """Label map: index into refs for pixels close to a reference color, else -1."""
    a = img.astype(float)
    palette = np.array(list(refs.values()) + [WHITE], dtype=float)
    d = np.sqrt(((a[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(-1))
    nearest = d.argmin(-1)
    ok = d.min(-1) < max_dist
    labels = np.where(ok & (nearest < len(refs)), nearest, -1)
    return labels


def runs(mask_col):
    """Contiguous True runs in a 1-D boolean array -> list of (start, end)."""
    idx = np.flatnonzero(mask_col)
    if idx.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]]
    return list(zip(starts, ends))


def trace(hit, x_range, max_jump=20, reacquire_after=4):
    """Follow one curve across columns. Returns {x: y_pixel} for found columns.

    Starts from the most reliable column (a single, solid run of the target
    color), then walks left and right, always taking the run nearest the last
    accepted position. If nothing acceptable is found for several columns in a
    row (the curve is hidden under another one), it re-acquires on the
    nearest run rather than staying stuck.
    """
    x0, x1 = x_range
    cols = {x: runs(hit[:, x]) for x in range(x0, x1 + 1)}
    singles = [x for x in range(x0, x1 + 1)
               if len(cols[x]) == 1 and cols[x][0][1] - cols[x][0][0] >= 1]
    if not singles:
        return {}
    mid = (x0 + x1) / 2
    seed_x = min(singles, key=lambda x: abs(x - mid))
    found = {}

    def walk(xs):
        prev, missed = None, 0
        for x in xs:
            r = cols[x]
            if not r:
                missed += 1
                continue
            centers = [(s + e) / 2 for s, e in r]
            if prev is None:
                pick = int(np.argmax([e - s for s, e in r]))
            else:
                pick = int(np.argmin([abs(c - prev) for c in centers]))
                limit = max_jump if missed < reacquire_after else np.inf
                if abs(centers[pick] - prev) > limit:
                    missed += 1
                    continue
            found[x] = centers[pick]
            prev, missed = centers[pick], 0

    walk(range(seed_x, x1 + 1))
    walk(range(seed_x, x0 - 1, -1))
    return found


def to_data(found, x_cal, y_cal):
    """Pixel -> data using two (pixel, value) pairs per axis."""
    (px1, vx1), (px2, vx2) = x_cal
    (py1, vy1), (py2, vy2) = y_cal
    xs = np.array(sorted(found))
    ys = np.array([found[x] for x in xs])
    wl = vx1 + (xs - px1) * (vx2 - vx1) / (px2 - px1)
    val = vy1 + (ys - py1) * (vy2 - vy1) / (py2 - py1)
    return xs, wl, val


def resample(wl, val, xs, start, stop, step, px_per_unit):
    """Resample to a regular grid; flag points more than 2 px from a real reading."""
    grid = np.arange(start, stop + step / 2, step)
    out = np.interp(grid, wl, val)
    nearest_gap_px = np.array([np.min(np.abs(wl - g)) for g in grid]) * px_per_unit
    interpolated = nearest_gap_px > 2.0
    return grid, out, interpolated


def write_csv(path, grid, values, interpolated, y_label):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wavelength_nm", y_label, "interpolated_gap"])
        for g, v, i in zip(grid, values, interpolated):
            w.writerow([f"{g:.0f}", f"{v:.4f}", int(i)])


def load(path):
    return np.array(Image.open(path).convert("RGB")).astype(int)
