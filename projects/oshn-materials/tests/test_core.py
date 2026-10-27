"""Sanity tests: the code must give the obviously-right answer in cases where
we know the answer without any data. The Gaussian curves below are test
fixtures only, never results."""
import numpy as np
import pytest

from oshn_materials import metrics, mixing, spectra

WL = spectra.GRID
FLUX = spectra.photon_flux(WL, spectra.load_am15g())
V = spectra.load_photopic()


def gaussian(center, width):
    return np.exp(-0.5 * ((WL - center) / width) ** 2)


# --- reference data -------------------------------------------------------

def test_am15g_total_matches_published_value():
    import pandas as pd
    df = pd.read_csv(spectra.DATA / "reference" / "astm_g173_am15g.csv")
    total = np.trapezoid(df["irradiance_W_m2_nm"], df["wavelength_nm"])
    assert total == pytest.approx(1000.37, rel=1e-3)  # ASTM G173 global total


def test_photopic_peaks_at_555nm():
    assert WL[np.argmax(V)] == 555


# --- metrics --------------------------------------------------------------

def test_clear_glass():
    s = metrics.summarize(WL, np.ones_like(WL), FLUX, V)
    assert s["PAR_transmitted_400_700"] == pytest.approx(1)
    assert s["AVT"] == pytest.approx(1)
    assert s["nonPAR_absorbed"] == pytest.approx(0)


def test_opaque_sheet():
    s = metrics.summarize(WL, np.zeros_like(WL), FLUX, V)
    assert s["PAR_transmitted_400_700"] == pytest.approx(0)
    assert s["nonPAR_absorbed"] == pytest.approx(1)


def test_ideal_par_filter():
    t = ((WL >= 400) & (WL <= 700)).astype(float)
    s = metrics.summarize(WL, t, FLUX, V)
    assert s["PAR_transmitted_400_700"] == pytest.approx(1)
    assert s["nonPAR_absorbed"] == pytest.approx(1)
    assert s["PAR_transmitted_400_750"] < 1  # blocks the 701-750 far-red


def test_missing_data_is_refused():
    t = np.ones_like(WL)
    t[(WL > 500) & (WL < 510)] = np.nan
    with pytest.raises(ValueError):
        metrics.par_transmission(WL, t, FLUX)


# --- mixing ---------------------------------------------------------------

def test_mix_endpoints_return_pure_spectra():
    a1, a2 = gaussian(430, 20), gaussian(670, 15)
    assert np.allclose(mixing.linear_mix(a1, a2, 1, 0), a1)
    assert np.allclose(mixing.linear_mix(a1, a2, 0, 1), a2)


def test_absorbance_transmittance_round_trip():
    a = np.array([0.0, 0.3, 1.0, 2.0])
    assert np.allclose(mixing.transmittance_to_absorbance(mixing.absorbance_to_transmittance(a)), a)


def test_weights_from_ratio():
    assert mixing.weights_from_ratio(1, 3) == (0.25, 0.75)


def test_fit_recovers_known_weights():
    a1, a2 = gaussian(430, 20), gaussian(670, 15)
    blend = mixing.linear_mix(a1, a2, 0.3, 0.9)
    w1, w2, err = mixing.fit_weights(blend, a1, a2)
    assert (w1, w2) == pytest.approx((0.3, 0.9), abs=1e-6)
    assert err < 1e-9


def test_fit_detects_nonlinear_blend():
    """A blend with a new band (as aggregation can cause) cannot be fit."""
    a1, a2 = gaussian(430, 20), gaussian(670, 15)
    blend = 0.5 * a1 + 0.5 * a2 + 0.4 * gaussian(720, 20)
    _, _, err = mixing.fit_weights(blend, a1, a2)
    assert err > 0.05
