"""Draw extracted traces on top of the source image, one panel per curve,
so every extraction can be checked by eye."""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def overlay(src, traces_json, out_png, titles=None, ncols=3):
    img = np.array(Image.open(src).convert("RGB"))
    faded = (0.45 * img + 0.55 * 255).astype(np.uint8)
    traces = json.loads(Path(traces_json).read_text())
    n = len(traces)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2 * ncols, 4.3 * nrows))
    for ax, (name, pts) in zip(np.ravel(axes), traces.items()):
        xs = np.array(sorted(int(k) for k in pts))
        ys = np.array([pts[str(x)] for x in xs])
        ax.imshow(faded)
        ax.plot(xs[::3], ys[::3], "o", ms=2.2, color="#ff7a00", mec="#5a2a00", mew=0.3)
        ax.set_title((titles or {}).get(name, name), fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
    for ax in np.ravel(axes)[n:]:
        ax.axis("off")
    fig.suptitle("Extracted points (orange) over the source figure", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_png, dpi=130)


if __name__ == "__main__":
    overlay(*sys.argv[1:4])
