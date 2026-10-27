# Source log

Status key: **verified** = opened and checked the specific claim used;
**summary only** = read an abstract or summary, not the full text;
**to do** = not yet located or checked.

## Core sources

| Source | Used for | Status |
|---|---|---|
| Shi, D. "Three-Dimensional Solar Harvesting with Transparent Spectral Selective Photovoltaics in Agrivoltaics." *Energies* 18, 1788 (2025). https://doi.org/10.3390/en18071788 | Motivation; Fig. 9 hybrid spectra (1:0, 1:1, 1:2, 1:3, 0:1) | verified (article text and Fig. 9 caption); reference list not yet read |
| Lin, J.; Wang, Y.; Lyu, M.; Deng, Z.; Shi, D. "Transparent porphyrin-based hybrid films for spectral selective solar harvesting and energy generation." *Sol. Energy Mater. Sol. Cells* 243, 111788 (2022). https://doi.org/10.1016/j.solmat.2022.111788 (Shi's ref. [31]) | Original data and methods behind Shi Fig. 9 | **verified, full text read** (copy in papers/, not for publishing). Shi's list gives "243, 15"; the paper itself is article 111788 |
| McCree, K. J. "The action spectrum, absorptance and quantum yield of photosynthesis in crop plants." *Agricultural Meteorology* 9, 191–216 (1972). | PAR = 400–700 nm | citation verified via multiple indexes; full text not read |
| Zhen, S.; Bugbee, B. "Far-red photons have equivalent efficiency to traditional photosynthetic photons: implications for re-defining photosynthetically active radiation." *Plant, Cell & Environment* (2020). https://doi.org/10.1111/pce.13730 | Extended PAR 400–750 nm | summary only |
| Traverse, C. J.; Pandey, R.; Barr, M. C.; Lunt, R. R. "Emergence of highly transparent photovoltaics for distributed applications." *Nature Energy* 2, 17104 (2017). https://doi.org/10.1038/s41560-017-0016-9 | AVT definition (Box 1) | verified |
| Ravishankar, E.; Charles, M.; et al. (O'Connor, Ade, Sederoff, corresponding). "Balancing crop production and energy harvesting in organic solar-powered greenhouses." *Cell Reports Physical Science* (2021). | Evidence that crops can grow under semitransparent OPV | summary only |
| Taniguchi, M.; Lindsey, J. S. *Photochem. Photobiol.* 94, 290–327 (2018). PhotochemCAD database. | Measured solution spectra | database pages verified; **reuse/republishing terms to do** |
| ASTM G173-03 AM1.5 reference spectrum (NREL) | Sunlight | verified (integrates to 1000.37 W/m²) |
| CIE 1924 photopic V(λ) | Eye sensitivity for AVT | verified (peaks at 555 nm) |

## Reference [31] details (from the paper itself)

- **Purpose of the paper:** photothermal heat generation (a 3D "photothermal generator"), not photovoltaics.
- **Materials:** chlorophyllin sodium copper (Sigma-Aldrich); β-form copper phthalocyanine (Tokyo Chemical Industry).
- **Fig. 2 (solution spectra):** in THF. Chlorophyllin fixed at 0.01 mg/mL; phthalocyanine added at 0, 0.005, 0.010, 0.020, 0.030 mg/mL, labeled 1:0, 1:0.5, 1:1, 1:2, 1:3. The ratio is mass of phthalocyanine added to a fixed chlorophyllin base, not a fraction of a fixed total.
- **0:1 (pure phthalocyanine) concentration:** not stated.
- **Y-axis:** "Absorption intensity (a.u.)".
- **Fig. 2 panel letters appear swapped** relative to the caption (see data/raw/lin2022_ref31/README.md). Visually confirmed 2026-10-05: the panel labeled (b) shows twin peaks near 630/730 nm (phthalocyanine). The vial photos are labeled consistently with the caption: (c) chlorophyllin:phthalocyanine vials are blue, as expected for copper phthalocyanine.
- **Fig. 5 (films):** spin-coated from THF with 10 wt% PEG at 3000 rpm for 10 s; ~556–825 nm thick; all films adjusted "via concentration and thickness" to 85% AVT. Absorption (a.u.) and transmittance (%) both shown, 300–1400 nm.
- **Shi Fig. 9** is Lin Fig. 2 panel (b), the correct chlorophyllin:phthalocyanine data, with all six ratios including 1:0.5 (visually confirmed 2026-10-05; an earlier note here saying 1:0.5 was omitted was wrong). Shi's text puts the chlorophyllin peaks 'near 400 nm and 650 nm'; Lin reports 404 and 630 nm. Shi attributes the rising absorption to 'structural similarities'; Lin's data alone does not test that.
- **Wording caution:** the paper says replacing chlorophyllin's center atom with copper "results in phthalocyanine." That is not accurate (phthalocyanine is a different macrocycle, and chlorophyllin sodium copper already contains copper). Don't repeat that sentence.
