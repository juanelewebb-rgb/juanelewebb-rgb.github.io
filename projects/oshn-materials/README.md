# OSHN Materials

Can a porphyrin-type absorber let crop light through and capture the rest?

This is the materials side of Project OSHN: a small, literature-based analysis of
light-absorbing blends for spectrally selective solar harvesting over crops,
inspired by Donglu Shi, "Three-Dimensional Solar Harvesting with Transparent
Spectral Selective Photovoltaics in Agrivoltaics," *Energies* 18, 1788 (2025),
https://doi.org/10.3390/en18071788

## Questions
1. Do chlorophyllin and phthalocyanine mix linearly in the data behind Shi Fig. 9 (Lin et al. 2022, ref. [31])? Where does it break?
2. Which available porphyrin / phthalocyanine pairs come closest to passing PAR while absorbing outside it?
3. How much do the answers change between PAR (400–700 nm) and extended PAR (400–750 nm)?

## What this is not
- Not a device model: no power conversion efficiency, no reflection, electrodes or substrate.
- Not quantum chemistry (no DFT/TD-DFT).
- Never invented data. Every spectrum is a cited measurement or labeled as a model output.

## Layout
```
data/reference/   sunlight (ASTM G173 AM1.5G) and eye sensitivity (CIE 1924 V(λ))
data/raw/         measured spectra, untouched: lin2022_ref31/ (digitized), photochemcad/
papers/           private copies of papers (git-ignored, never published)
src/oshn_materials/
  spectra.py      loading + common 1 nm wavelength grid + photon flux
  mixing.py       linear mixing model and weight fitting
  metrics.py      PAR transmitted, extended PAR, AVT, non-PAR absorbed
notebooks/
  00_reference_check.ipynb   sanity checks on reference data (runs now)
  01_linear_mixing_lin2022.ipynb  linear-mixing test on Lin et al. 2022 (ref. [31]) data
tests/            pytest sanity tests
docs/source_log.md  every source, and whether it has been verified
```

## Run
```
pip install -r requirements.txt
pytest
jupyter lab notebooks/
```
