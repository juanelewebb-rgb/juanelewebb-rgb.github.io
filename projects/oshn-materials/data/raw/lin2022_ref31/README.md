# Lin et al. (2022), Shi's reference [31]: digitized curves

Lin, J.; Wang, Y.; Lyu, M.; Deng, Z.; Shi, D. "Transparent porphyrin-based hybrid
films for spectral selective solar harvesting and energy generation."
Sol. Energy Mater. Sol. Cells 243, 111788 (2022). https://doi.org/10.1016/j.solmat.2022.111788

This is the original source of Shi (2025) Fig. 9. Digitize from here, not from Shi.

## Target 1: Fig. 2, solution spectra (for notebook 01)
WARNING: the panel letters inside Fig. 2 appear swapped relative to the caption.
The chlorophyllin:phthalocyanine curves are the panel labeled "(b)" in the image
(twin peaks near 630 and 730 nm). The panel labeled "(a)" (broad hump near
1100 nm) matches the text's description of Fe3O4@Cu2-xS. Fig. 5 (films) is
labeled consistently with its caption, which supports this reading.
Visually confirmed 2026-10-05: digitize the panel labeled (b).

Files (wavelength nm, then "Absorption intensity (a.u.)" exactly as plotted):
fig2_1-0.csv, fig2_1-0.5.csv, fig2_1-1.csv, fig2_1-2.csv, fig2_1-3.csv, fig2_0-1.csv

## Target 2: Fig. 5b, film transmittance (for crop-light metrics, later)
Transmittance (%) of the chlorophyllin:phthalocyanine films, 300–1400 nm,
including the PEG "control". These are real film measurements, so PAR and AVT
can be computed directly. Note: T includes the glass substrate (compare to control).
Files: fig5b_1-0.csv, fig5b_1-0.5.csv, fig5b_1-1.csv, fig5b_1-2.csv, fig5b_1-3.csv,
fig5b_0-1.csv, fig5b_control.csv

## How to digitize (WebPlotDigitizer, https://automeris.io/WebPlotDigitizer)
1. Screenshot the panel at high zoom and load it.
2. Calibrate axes with the four points marked in source_images/calibration_fig2b.png and calibration_fig5b.png:
   Fig. 2b: X1 = 400, X2 = 1200, Y1 = 0, Y2 = 1.  Fig. 5b: X1 = 400, X2 = 1300, Y1 = 10, Y2 = 90.
   (The end ticks sit on the plot frame, so interior ticks are easier to click precisely.)
3. Trace one curve at a time (the color picker helps); export CSV.
4. Save with the names above. Do not smooth, rescale or edit the numbers.

## Color-extracted curves (extracted/)
Made by scripts/extract_lin2022_fig2b.py and scripts/extract_lin2022_fig5b.py
(method in scripts/digitize_by_color.py). Each CSV has wavelength_nm, the value
as plotted, and interpolated_gap = 1 where the curve was hidden under another
curve and the value was filled by a straight line. Visual checks:
figures/qa_fig2_extraction.png and figures/qa_fig5b_extraction.png.
Expected reading error: about one line width (~±2 nm; ~±0.01 a.u. in Fig. 2,
~±0.5% T in Fig. 5b). Fig. 5b curves overlap heavily above 800 nm, so more of
that range is interpolated (values there all sit within ~85–89% T).
Status: awaiting a hand spot-check in WebPlotDigitizer before results are used.
Hand-digitized files placed directly in this folder take priority over extracted/.
