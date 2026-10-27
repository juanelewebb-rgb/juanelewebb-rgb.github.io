"""Crop-vs-power light metrics for a transmission spectrum T(lambda).

All metrics weight by the solar PHOTON flux (AM1.5G), because plants count
photons. Sources:
  - PAR 400-700 nm: McCree (1972), Agricultural Meteorology 9, 191-216.
  - Extended PAR 400-750 nm: Zhen & Bugbee (2020), Plant, Cell & Environment.
  - AVT: Traverse et al. (2017), Nature Energy 2, 17104, Box 1:
        AVT = integral(T * P * S) / integral(P * S)
    with P the photopic response and S the solar photon flux.

What these numbers are NOT: power conversion efficiency. Absorbing a photon
is not the same as turning it into electricity.
"""
import numpy as np

PAR = (400.0, 700.0)
EXTENDED_PAR = (400.0, 750.0)


def _band(wavelength, lo, hi):
    wavelength = np.asarray(wavelength)
    return (wavelength >= lo) & (wavelength <= hi)


def _require_coverage(transmittance, mask, label):
    if np.isnan(np.asarray(transmittance)[mask]).any():
        raise ValueError(
            f"Spectrum has missing values inside {label}; "
            "refusing to compute a number from incomplete data."
        )


def band_transmission(wavelength, transmittance, flux, band):
    """Fraction of solar photons inside `band` that pass through (0-1)."""
    m = _band(wavelength, *band)
    _require_coverage(transmittance, m, f"{band[0]:.0f}-{band[1]:.0f} nm")
    t, f, w = np.asarray(transmittance)[m], np.asarray(flux)[m], np.asarray(wavelength)[m]
    return float(np.trapezoid(t * f, w) / np.trapezoid(f, w))


def par_transmission(wavelength, transmittance, flux, band=PAR):
    """Share of photosynthetic photons that reach the crop."""
    return band_transmission(wavelength, transmittance, flux, band)


def average_visible_transmittance(wavelength, transmittance, flux, photopic):
    """AVT as defined by Traverse et al. (2017)."""
    v = np.asarray(photopic)
    m = v > 0
    _require_coverage(transmittance, m, "the visible range")
    t, f, w, v = (np.asarray(x)[m] for x in (transmittance, flux, wavelength, v))
    return float(np.trapezoid(t * v * f, w) / np.trapezoid(v * f, w))


def absorbed_fraction(wavelength, transmittance, flux, bands):
    """Fraction of solar photons absorbed across one or more bands.

    Used for "light available to harvest": photons outside PAR that the
    material captures. An upper bound on what a device could use.
    """
    absorbed, total = 0.0, 0.0
    for lo, hi in bands:
        m = _band(wavelength, lo, hi)
        _require_coverage(transmittance, m, f"{lo:.0f}-{hi:.0f} nm")
        t, f, w = (np.asarray(x)[m] for x in (transmittance, flux, wavelength))
        absorbed += np.trapezoid((1 - t) * f, w)
        total += np.trapezoid(f, w)
    return float(absorbed / total)


def summarize(wavelength, transmittance, flux, photopic, upper_nm=950.0):
    """The four numbers reported for every material or blend."""
    return {
        "PAR_transmitted_400_700": par_transmission(wavelength, transmittance, flux, PAR),
        "PAR_transmitted_400_750": par_transmission(wavelength, transmittance, flux, EXTENDED_PAR),
        "AVT": average_visible_transmittance(wavelength, transmittance, flux, photopic),
        "nonPAR_absorbed": absorbed_fraction(
            wavelength, transmittance, flux, [(300.0, 399.0), (701.0, upper_nm)]
        ),
    }
