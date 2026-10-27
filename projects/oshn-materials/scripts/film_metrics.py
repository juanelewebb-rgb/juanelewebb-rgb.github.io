"""Crop-light numbers for Lin et al. (2022) films (Fig. 5b, color-extracted).

Each film's transmittance is divided by the blank PEG control film, so glass
and PEG losses cancel and what is left is the effect of the dye layer.
Bands (photon-weighted with AM1.5G sunlight):
  PAR            400-700 nm   (McCree 1972)
  non-PAR        350-399 nm and 701-1000 nm
                 (below 350 nm the glass itself absorbs; the extracted data
                  stop at 1000 nm in this analysis)
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from oshn_materials import spectra  # noqa: E402

EXT = ROOT / "data/raw/lin2022_ref31/extracted"
WL = spectra.GRID
FLUX = spectra.photon_flux(WL, spectra.load_am15g())


def load(name):
    d = pd.read_csv(EXT / f"fig5b_{name}.csv")
    return spectra.to_grid(d["wavelength_nm"].to_numpy(), d["transmittance_pct"].to_numpy() / 100)


def absorbed(t_rel, lo, hi):
    m = (WL >= lo) & (WL <= hi)
    return np.trapezoid((1 - t_rel[m]) * FLUX[m], WL[m]), np.trapezoid(FLUX[m], WL[m])


def main():
    control = load("control")
    rows = []
    for key, label in [("1-0", "1:0"), ("1-0.5", "1:0.5"), ("1-1", "1:1"),
                       ("1-2", "1:2"), ("1-3", "1:3"), ("0-1", "0:1")]:
        t_rel = np.clip(load(key) / control, 0, 1)
        par, par_tot = absorbed(t_rel, 400, 700)
        uv, uv_tot = absorbed(t_rel, 350, 399)
        nir, nir_tot = absorbed(t_rel, 701, 1000)
        rows.append({
            "film": label,
            "PAR_blocked_pct": 100 * par / par_tot,
            "nonPAR_captured_pct": 100 * (uv + nir) / (uv_tot + nir_tot),
            "PAR_share_of_absorbed_pct": 100 * par / (par + uv + nir),
            "PAR_lost_umol_m2_s": par,
            "nonPAR_captured_umol_m2_s": uv + nir,
        })
    df = pd.DataFrame(rows)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    df.round(2).to_csv(out / "film_metrics_lin2022.csv", index=False)
    print(df.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
