"""Extract film transmittance curves (chlorophyllin:phthalocyanine films and
PEG control) from Lin et al. (2022) Fig. 5b."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from digitize_by_color import classify, load, resample, to_data, trace, write_csv
from extract_lin2022_fig2b import calibration

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/raw/lin2022_ref31/source_images/lin2022_fig5b_film_transmittance.png"
OUT = ROOT / "data/raw/lin2022_ref31/extracted"

X_TICKS = [(190, 400), (253, 500), (318, 600), (381, 700), (445, 800),
           (508, 900), (573, 1000), (636, 1100), (700, 1200), (763, 1300)]
Y_TICKS = [(467, 10), (416, 20), (366, 30), (316, 40), (266, 50),
           (165, 70), (115, 80), (64, 90)]
COLORS = {"1-0": (0, 0, 0), "1-0.5": (255, 0, 0), "1-1": (0, 255, 0),
          "1-2": (0, 0, 255), "1-3": (0, 255, 255), "0-1": (255, 0, 255),
          "control": (255, 128, 0)}


def main():
    img = load(SRC)
    h, w, _ = img.shape
    x_cal, nm_per_px = calibration(X_TICKS)
    y_cal, _ = calibration(Y_TICKS)
    labels = classify(img, COLORS, max_dist=110)

    mask = np.ones((h, w), bool)
    mask[:14, :] = False; mask[518:, :] = False          # frame top / bottom axis
    mask[:, :126] = False; mask[:, 828:] = False         # frame sides
    mask[295:, 680:] = False                             # legend
    mask[:45, :190] = False                              # "(b)" label
    for x, _ in X_TICKS:                                 # bottom tick marks
        mask[505:518, int(x) - 2:int(x) + 3] = False
    for y, _ in Y_TICKS:                                 # left tick marks
        mask[int(y) - 2:int(y) + 3, 124:137] = False

    OUT.mkdir(parents=True, exist_ok=True)
    traces, summary = {}, {}
    for i, name in enumerate(COLORS):
        found = trace((labels == i) & mask, (126, 827))
        xs, wl, val = to_data(found, x_cal, y_cal)
        grid, out, interp = resample(wl, val, xs, 300, 1400, 2, 1 / nm_per_px)
        write_csv(OUT / f"fig5b_{name}.csv", grid, out, interp, "transmittance_pct")
        traces[name] = {int(x): float(found[x]) for x in found}
        summary[name] = {"columns_found_pct": round(100 * len(found) / 702, 1),
                         "grid_points_interpolated_pct": round(100 * interp.mean(), 1)}
    (OUT / "fig5b_traces_px.json").write_text(json.dumps(traces))
    (OUT / "fig5b_extraction_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
