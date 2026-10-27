#!/usr/bin/env bash
# One-shot setup for Ubuntu / WSL Ubuntu. Run from the project folder:  bash scripts/setup_ubuntu.sh
set -euo pipefail

sudo apt update
# system libraries Open3D / OpenCV need on a minimal Ubuntu
sudo apt install -y python3-venv python3-pip unzip libusb-1.0-0 libgl1 libgomp1 libglib2.0-0 libx11-6

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# no screen on a server/WSL: use the headless OpenCV build (avoids libGL errors)
pip uninstall -y opencv-python
pip install opencv-python-headless
pip install -e . pytest

python -c "import open3d, cv2; print('imports ok: open3d', open3d.__version__, '| opencv', cv2.__version__)"
echo "Done. Activate with:  source .venv/bin/activate"
