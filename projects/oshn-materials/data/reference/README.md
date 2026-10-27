# Reference data

| File | What | Source |
|---|---|---|
| astm_g173_am15g.csv | AM1.5 global spectral irradiance, W m^-2 nm^-1, 280–4000 nm | ASTM G173-03, copied from the NREL file bundled with pvlib-python 0.13. Integrates to 1000.37 W/m² (checked in tests). |
| cie1924_photopic.csv | Photopic luminosity function V(λ), 360–830 nm | CIE 1924 photopic standard observer, as distributed in the colour-science Python package. |
