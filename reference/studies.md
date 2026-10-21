# Studies

A study answers one owner question with one page. Render every option from the same view, compose a labeled page, and let the owner choose.

## Option flags

1. Add a flag per question, such as `--vanity a|b|c`. Keep each option's values in the constants block.
2. Render the same view once per option, at preview settings.
3. Compose the renders into one page.
4. After the owner chooses, set the choice as the flag default and log it in `context/decisions.md`.

To study one element at several sites, model it around the origin in a function. Call `placed(build, x, y, z, rot)` per site.

## Study pages

```
uvx --with pillow python -I lib/compose.py deliverables/<date>_studies/kitchen.jpg \
  --title="Vanity options" --width=2400 \
  "#Front view" "A=scratch/v_a.png" "B=scratch/v_b.png" "|" \
  "#Plan" "A=scratch/p_a.png" "B=scratch/p_b.png" "C=-"
```

- `|` ends a row. `#Heading` adds a section heading. `Label=-` leaves a blank, labeled cell.
- Each row scales so its cells share the page width.
- Send one page per question.

## The figure

`mannequin(pose, height)` builds a neutral clay figure at the real user's height, posed with two-bone IK.

```python
from mannequin import mannequin, EXAMPLE_POSE
mannequin(dict(EXAMPLE_POSE, root=(1.0, 0.75)), height=1.52)
```

- Keep project poses in the project script. `EXAMPLE_POSE` documents the format, in metres.
- On an upper floor, set the pose's `floor_z`. Feet and the standing pelvis sit relative to it.
- A pose sets the pelvis, facing, lean, head tilt, ankles, wrists and fingertips, and an elbow pole per arm.
- An out-of-reach target clamps to full extension, so check that the hands reach what they should.
- Run `clash_check(("man_",), (...fixture prefixes...))` on every figure view, and re-pose until it is empty.
- The clash check also reports a part fully inside a closed object. It cannot test containment in open meshes.

`person(mat, x, y, h)` is a simpler scale figure: a cylinder and a sphere. Use it for scale in wide views.

## Scale and realism

- Add scale props, and draw running water as a curve with `tube`.
- Use realistic light wattages, and test exposure with a grey-material pass.
- Use one fixed sun time for all renders. `sun(elevation_deg, azimuth_deg, plan_north_deg=0.0)` takes the solar position; record it in the dimensions file.
- Use `room_fill_lights` for even interior fill. The panels stay out of the camera and out of reflections.
- Glass blocks the sun. Use `opening_light` for daylight through skylights and glazed openings.
- For an enclosed room or a night view, pass a near-black world to `setup_cycles`, such as `sky=(0.02, 0.018, 0.015)`. The default sky lights the room as if it were outdoors.

## Walkthrough video

Optional. A walkthrough keyframes the camera (time, position, heading, pitch) and any moving doors, drawers, or cabinets, then joins the frames with ffmpeg into an MP4.

- Make a walkthrough only after the design settles. Each render takes hours: 40 to 66 s of video took 1 h 50 min to 3.5 h.
- Before you launch a render, estimate its runtime from one test frame, and tell the owner.
- Render frames into a git-ignored `frames/` folder.

## Textures

- Keep a texture schedule: one CC0 texture per surface, from ambientCG or Poly Haven, confirmed in a test render.
- For tile with a real setout, use `tile_wall` with `image_tile_material`. Each piece is its own object, which feeds the cutting plans.
- For surfaces without a setout, use `projected_tile_material` or the procedural `stone_tile`, `planks`, and `wood_material`.
- Set `stone_tile`'s `plane` to match the wall's orientation. A wrong plane shows streaks instead of tiles.
