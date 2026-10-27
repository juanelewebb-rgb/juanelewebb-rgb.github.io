"""Command line:  python -m recon3d <command> ..."""
import argparse
import sys

from . import images


def main(argv=None):
    ap = argparse.ArgumentParser(prog="recon3d", description="3D reconstruction from 2D images")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check your photos against the capture rules")
    c.add_argument("images")

    r = sub.add_parser("run", help="run the whole pipeline")
    r.add_argument("images", help="folder of photos (jpg/png)")
    r.add_argument("--out", default="output/run1")
    r.add_argument("--max-dim", type=int, default=1600, help="downscale longest side to this (speed)")
    r.add_argument("--window", type=int, default=None,
                   help="only match images within N positions of each other (for ordered orbit photos)")
    r.add_argument("--features", type=int, default=6000)
    r.add_argument("--depth", type=int, default=8, help="Poisson depth (7=fast, 9-10=detailed)")
    r.add_argument("--skip-dense", action="store_true", help="mesh straight from the sparse SfM points")
    r.add_argument("--no-video", action="store_true")

    d = sub.add_parser("features-demo", help="save keypoint + match pictures for two photos (like the seminar slides)")
    d.add_argument("image_a")
    d.add_argument("image_b")
    d.add_argument("--out", default="output/features_demo")

    s = sub.add_parser("synthetic", help="generate a fake test photo set")
    s.add_argument("out", nargs="?", default="data/synthetic")
    s.add_argument("-n", type=int, default=36)

    a = ap.parse_args(argv)
    if a.cmd == "check":
        warns = images.check_images(a.images)
        print("\n".join(warns) if warns else "All good - photos look usable.")
    elif a.cmd == "features-demo":
        from pathlib import Path
        import cv2
        from . import features, matching
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        A, B = images.load_image(Path(a.image_a)), images.load_image(Path(a.image_b))
        fa, fb = features.extract(A), features.extract(B)
        ia, ib = matching.match_pair(fa, fb)
        ja, jb, _ = matching.verify_pair(fa, fb, ia, ib)
        print(f"keypoints: {len(fa.xy)} / {len(fb.xy)}   ratio-test matches: {len(ia)}   after geometric check: {len(ja)}")
        cv2.imwrite(str(out / "keypoints_a.jpg"), features.draw_keypoints(A, fa))
        cv2.imwrite(str(out / "matches_raw.jpg"), matching.draw_matches(A, B, fa, fb, ia, ib))
        cv2.imwrite(str(out / "matches_verified.jpg"), matching.draw_matches(A, B, fa, fb, ja, jb))
        print("wrote pictures to", out)
    elif a.cmd == "synthetic":
        from .synthetic import make_dataset
        print("wrote", make_dataset(a.out, a.n))
    elif a.cmd == "run":
        from .pipeline import run
        run(a.images, a.out, a.max_dim, a.window, a.features, a.depth, not a.no_video, a.skip_dense)


if __name__ == "__main__":
    sys.exit(main())
