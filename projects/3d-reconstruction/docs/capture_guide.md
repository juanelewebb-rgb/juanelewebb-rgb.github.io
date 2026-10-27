# Capture guide (from the assignment handout)

Goal: at least **20** photos (PNG/JPG) of the same object. Polycam accepts 20-150; 40-80 is a good target for a plant.

## Rules
1. **Center** - keep the subject in the middle of the frame, filling roughly the middle 1/3-2/3.
2. **Walk around** - take three photos at a high, middle and low position, step to the next spot, repeat in a circle.
   Neighbouring viewpoints should be within ~30 degrees of each other as seen from the object.
3. **Overlap** - 70-80 % overlap between photos. A feature can only be reconstructed if >= 3 cameras see it.
4. **Orientation** - every camera points at the object (not along the walls).
5. **Same distance** - similar distance for every shot; do not zoom between shots.
6. **No shadows / reflections** - soft, even light; avoid direct sun and shiny backgrounds. Moving shadows break matching.
7. **No blur** - hold still, good light, tap to focus. `python -m recon3d check data/images` flags photos that are
   much blurrier than the rest.
8. **More photos** = better results.

## Plant-specific tips
* Put the pot on a **textured, non-shiny surface** (newspaper, patterned cloth) - a blank white table gives the
  software nothing to match on.
* Place a few small objects or printed markers around the plant (outside the foliage) as extra anchor features.
* Leaves move: shoot quickly, indoors, no fans/wind.
* A turntable plus a fixed camera is NOT equivalent: the background then stays still while the plant moves, which
  confuses SfM. Move the camera, not the plant.
* Keep camera settings fixed (no auto-zoom, no switching between lenses).
* Add a ruler in the scene if you want to scale the model to real units later.
