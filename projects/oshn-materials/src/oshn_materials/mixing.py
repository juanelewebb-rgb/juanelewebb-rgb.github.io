"""First-order (linear) mixing of absorption spectra.

Assumption being tested, not assumed true: if two absorbers do not interact,
their absorbances add (Beer-Lambert law). For a blend,

    A_mix(lambda) = w1 * A1(lambda) + w2 * A2(lambda)

where A1 and A2 are the spectra of each pure material and w1, w2 say how
much of each pure spectrum is present. If the materials aggregate or pass
energy between each other, the real blend will not match this prediction,
and measuring that mismatch is the point of the Shi validation.
"""
import numpy as np
from scipy.optimize import nnls


def absorbance_to_transmittance(absorbance):
    """T = 10^(-A). Ignores reflection and scattering."""
    return np.power(10.0, -np.asarray(absorbance, dtype=float))


def transmittance_to_absorbance(transmittance):
    """A = -log10(T). T is clipped to avoid log(0)."""
    t = np.clip(np.asarray(transmittance, dtype=float), 1e-12, None)
    return -np.log10(t)


def linear_mix(a1, a2, w1, w2):
    """Predicted blend absorbance: w1*A1 + w2*A2."""
    return w1 * np.asarray(a1) + w2 * np.asarray(a2)


def weights_from_ratio(r1, r2):
    """Turn a ratio like 1:3 into fractions (0.25, 0.75).

    These fractions only equal the mixing weights if BOTH of these hold:
      1. the ratio is on the right basis (molar, if the pure spectra are
         per-mole; it is NOT the same as a mass or volume ratio), and
      2. the pure spectra were measured at the same total amount as the blend.
    Lin et al. (2022), Shi's ref. [31], used a different design: a FIXED
    amount of chlorophyllin plus increasing phthalocyanine. For that design,
    use fit_weights and check that the phthalocyanine weight grows in
    proportion to the amount added (notebook 01, test 2).
    """
    total = r1 + r2
    if total <= 0:
        raise ValueError("Ratio parts must add up to a positive number")
    return r1 / total, r2 / total


def fit_weights(a_measured, a1, a2):
    """Best non-negative weights so that w1*A1 + w2*A2 matches a measured blend.

    This works even when the ratio basis is unknown: if NO pair of
    non-negative weights reproduces the measured shape, the materials are not
    mixing linearly. Wavelengths where any input is NaN are ignored.

    Returns (w1, w2, rmse).
    """
    a_measured, a1, a2 = (np.asarray(x, dtype=float) for x in (a_measured, a1, a2))
    ok = ~(np.isnan(a_measured) | np.isnan(a1) | np.isnan(a2))
    if ok.sum() < 3:
        raise ValueError("Not enough overlapping wavelengths to fit")
    design = np.column_stack([a1[ok], a2[ok]])
    (w1, w2), _ = nnls(design, a_measured[ok])
    return w1, w2, rmse(a_measured, linear_mix(a1, a2, w1, w2))


def rmse(measured, predicted):
    """Root-mean-square difference, ignoring NaN wavelengths."""
    diff = np.asarray(measured, dtype=float) - np.asarray(predicted, dtype=float)
    diff = diff[~np.isnan(diff)]
    return float(np.sqrt(np.mean(diff ** 2)))
