"""Loading spectra and putting them on one shared wavelength grid.

Every calculation in this project compares spectra wavelength by wavelength,
so everything is first interpolated onto the same grid (GRID, 1 nm steps).
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = PROJECT_ROOT / "data"

# 300-1000 nm covers UV-A through near-infrared, which is where the
# porphyrin / phthalocyanine absorption bands we care about sit.
GRID = np.arange(300.0, 1000.0 + 1, 1.0)

# Physical constants (exact SI values)
PLANCK = 6.62607015e-34       # J*s
LIGHT_SPEED = 2.99792458e8    # m/s
AVOGADRO = 6.02214076e23      # 1/mol


def load_two_column(path):
    """Read a plain-text spectrum: first column wavelength (nm), second a value.

    Works for WebPlotDigitizer exports and simple TXT/CSV files. Any line
    that does not start with two numbers (headers, comments) is skipped.
    Returns (wavelength, value) sorted by wavelength.
    """
    wavelengths, values = [], []
    for line in Path(path).read_text(errors="replace").splitlines():
        parts = line.replace(",", " ").replace(";", " ").split()
        if len(parts) < 2:
            continue
        try:
            wl, val = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        wavelengths.append(wl)
        values.append(val)
    if not wavelengths:
        raise ValueError(f"No numeric data found in {path}")
    wl = np.array(wavelengths)
    val = np.array(values)
    order = np.argsort(wl)
    return wl[order], val[order]


def to_grid(wavelength, values, grid=GRID):
    """Linearly interpolate onto `grid`.

    Wavelengths outside the original data become NaN (not zero), so missing
    coverage can never be mistaken for "no absorption".
    """
    return np.interp(grid, wavelength, values, left=np.nan, right=np.nan)


def load_am15g(grid=GRID):
    """ASTM G173-03 AM1.5 global solar spectral irradiance, W m^-2 nm^-1."""
    df = pd.read_csv(DATA / "reference" / "astm_g173_am15g.csv")
    return to_grid(df["wavelength_nm"].to_numpy(), df["irradiance_W_m2_nm"].to_numpy(), grid)


def load_photopic(grid=GRID):
    """CIE 1924 photopic luminosity function V(lambda); zero outside 360-830 nm."""
    df = pd.read_csv(DATA / "reference" / "cie1924_photopic.csv")
    v = to_grid(df["wavelength_nm"].to_numpy(), df["V_lambda"].to_numpy(), grid)
    return np.nan_to_num(v, nan=0.0)


def photon_flux(wavelength_nm, irradiance):
    """Convert spectral irradiance (W m^-2 nm^-1) to photon flux (umol m^-2 s^-1 nm^-1).

    Each photon carries energy h*c/lambda, so photons = energy * lambda / (h*c).
    Plants respond to photon counts, not energy, which is why PAR is
    expressed in umol of photons.
    """
    wavelength_m = np.asarray(wavelength_nm) * 1e-9
    photons_per_s = np.asarray(irradiance) * wavelength_m / (PLANCK * LIGHT_SPEED)
    return photons_per_s / AVOGADRO * 1e6
