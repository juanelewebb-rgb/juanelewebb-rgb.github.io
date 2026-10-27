"""Extract the six chlorophyllin:phthalocyanine curves from Lin et al. (2022) Fig. 2,
the panel labeled (b). Calibration ticks were located in the image (see README)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from digitize_by_color import classify, load, resample, to_data, trace, write_csv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/lin2022_ref31/source_images/lin2022_fig2_panelb_hybrid_solutions.png"
OUT = ROOT / "data/raw/lin2022_ref31/extracted"

# Tick marks found in the image: (pixel, value)
X_TICKS = [(152.5, 400), (225.5, 500), (299, 600), (372, 700), (445, 800),
           (518.5, 900), (591.5, 1000), (664.5, 1100), (737.5, 1200)]
Y_TICKS = [(526.5, 0.0), (356, 0.5), (184.5, 1.0)]
COLORS = {"1-0": (0, 0, 0), "1-0.5": (255, 0, 0), "1-1": (0, 255, 0),
          "1-2": (0, 0, 255), "1-3": (0, 255, 255), "0-1": (255, 0, 255)}


def calibration(ticks):
    p, v = np.array(ticks).T
    slope, intercept = np.polyfit(p, v, 1)
    return ((0, intercept), (1000, intercept + 1000 * slope)), slope


def main():
    img = load(SRC)
    h, w, _ = img.shape
    x_cal, nm_per_px = calibration(X_TICKS)
    y_cal, _ = calibration(Y_TICKS)
    labels = classify(img, COLORS, max_dist=110)

    mask = np.ones((h, w), bool)
    mask[:14, :] = False; mask[549:, :] = False          # frame top, bottom axis + ticks
    mask[:, :116] = False; mask[:, 812:] = False         # frame sides
    mask[:300, 640:] = False                             # legend
    mask[:70, :190] = False                              # "(b)" label
    mask[180:190, 114:128] = False; mask[352:361, 114:128] = False  # y ticks

    OUT.mkdir(parents=True, exist_ok=True)
    traces, summary = {}, {}
    for i, name in enumerate(COLORS):
        found = trace((labels == i) & mask, (116, 811))
        xs, wl, val = to_data(found, x_cal, y_cal)
        grid, out, interp = resample(wl, val, xs, 350, 1300, 2, 1 / nm_per_px)
        write_csv(OUT / f"fig2_{name}.csv", grid, out, interp, "absorption_au")
        traces[name] = {int(x): float(found[x]) for x in found}
        summary[name] = {"columns_found_pct": round(100 * len(found) / 696, 1),
                         "grid_points_interpolated_pct": round(100 * interp.mean(), 1)}
    (OUT / "fig2_traces_px.json").write_text(json.dumps(traces))
    (OUT / "fig2_extraction_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
