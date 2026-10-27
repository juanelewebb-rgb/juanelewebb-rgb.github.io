"""Website figure: measured transmittance of Lin et al. (2022) films (Fig. 5b),
re-plotted from color-extracted data, with the PAR band shaded."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "data/raw/lin2022_ref31/extracted"
OUT = ROOT / "figures/film_transmittance_par.png"

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
SERIES = [("1-0", "Chlorophyllin only (1:0)", "#2a78d6"),
          ("1-3", "Hybrid (1:3)", "#eb6834"),
          ("0-1", "Phthalocyanine only (0:1)", "#1baf7a")]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, ax = plt.subplots(figsize=(8.8, 4.6), dpi=200)
ax.axvspan(400, 700, color="#e3ece4", zorder=0)
ax.text(550, 101.2, "PAR · light plants use (400–700 nm)", ha="center", va="bottom",
        color="#3f6b4a", fontsize=10, fontweight="bold")

c = pd.read_csv(EXT / "fig5b_control.csv").query("350 <= wavelength_nm <= 1000")
ax.plot(c.wavelength_nm, c.transmittance_pct, color=MUTED, lw=1.6, ls=(0, (4, 3)),
        label="Blank film (control)", zorder=2)
for key, label, color in SERIES:
    d = pd.read_csv(EXT / f"fig5b_{key}.csv").query("350 <= wavelength_nm <= 1000")
    ax.plot(d.wavelength_nm, d.transmittance_pct, color=color, lw=2, label=label, zorder=3)

ax.annotate("Chlorophyllin's main band\nsits inside PAR (blue light)", xy=(405, 48), xytext=(470, 52),
            fontsize=9.5, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
for x, y in [(630, 80.0), (722, 80.3)]:
    ax.annotate("", xy=(x, y - 0.6), xytext=(745, 70.5),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(748, 69, "Phthalocyanine bands: ~630 nm\n(inside PAR) and ~725 nm (far-red)",
        fontsize=9.5, color=INK2, va="top")

ax.set_xlim(350, 1000); ax.set_ylim(40, 104)
ax.set_xlabel("Wavelength (nm)", color=INK2); ax.set_ylabel("Transmittance (%)", color=INK2)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#bdbcb6")
ax.tick_params(colors=INK2)
ax.legend(loc="lower right", frameon=False, fontsize=9.5)
fig.tight_layout()
fig.savefig(OUT, facecolor="white")
print(OUT)
