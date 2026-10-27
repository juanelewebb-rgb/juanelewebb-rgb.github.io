# Polycam baseline (assignment steps)

1. Go to <https://poly.cam/tools/photogrammetry>, **sign up** (email/Google/Apple) and **Open workspace**.
2. **Create -> Create model from images/video**.
3. **Choose from file system**, select all photos (20 min, 150 max, PNG/JPG).
4. Name the model, choose detail (**Medium** is a good balance; Full/Raw are slower). Leave *Isolate object* off unless
   you flipped the object, and *Sequential* off unless photos are in shooting order.
5. **Upload & Process** - roughly 10-40 minutes.
6. Rotate the finished model in the browser.
7. **Download -> Video (under "OTHER") -> Export**. Rename the file to your name and upload it to the assignment folder.
   (Mesh formats like OBJ/GLTF/PLY are Pro features; video export is free.)

## Compare with this repo
Run the same photos through `python -m recon3d run` and note differences (completeness, holes, thin parts, scale,
runtime) in [`experiments.md`](experiments.md).
