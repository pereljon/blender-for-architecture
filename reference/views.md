# Views

Define every view as an entry in the script's `VIEWS` dict, and select it with `--view`. `add_camera(VIEWS[name], res)` builds the camera and sets the resolution. Render one view per Blender run.

A plan entry's `width` is the view's span on its longer side, in project units.

## Perspective views

```python
VIEWS = {"vanity": dict(loc=(1.2, 3.4, 1.55), target=(1.2, 0.5, 1.2), lens=24, aspect=0.625, shift_y=0.05)}
```

- Keep the camera level, and frame with `shift_x` and `shift_y` instead of tilting. Tilted cameras make walls lean.
- Place the camera close enough to read the action, such as a hand at a basin.
- Keep the camera outside every object. Check again after moving furniture.
- `hide` lists name prefixes hidden from the camera in this view only, such as a wall between the camera and the room. A hidden object still casts shadows, blocks light, and shows in mirrors.

## Plan views

A plan view is an orthographic camera looking down, cut at a fixed height (5'-0" or 1.25 m is usual).

Every plan entry does these steps:
1. The camera's `clip_start` sits at the cut height, which gives a true cut.
2. `plan_cut` hides every light and every object whose bottom is above the cut, such as ceilings and headers.
3. `plan_light` adds one even overhead light, sized to cover the plan, and a dim grey world.

The clip alone is not enough. `clip_start` removes geometry only from camera rays, so a ceiling above the cut still blocks light and casts shadows.

The clip shows each object that crosses the cut as a dark section, because the inside of the object is unlit. That reads as solid poché for walls. When an item must read from above, add its prefix to `drop`: a door leaf, a mirror, a fixture, or walls that should render grey.

| Entry key | Does | Use when |
|---|---|---|
| `drop` | Squashes the named tall items to end just under the cut. | Closets, fixtures, and equipment must still read in plan. |
| `keep` | Keeps the named objects above the cut visible. | An element above the cut must show, such as a stair. |
| `hide` | Removes the named objects from this plan render. | Scale figures, fill lights, wall tile, upper cabinets. |

```python
VIEWS["plan"] = dict(plan=True, center=(15.5, 12.4), width=84.0, cut=5.0, aspect=0.75,
                     hide=("ceil_", "L_", "person_"), drop=("wic_hang", "fixture_"), keep=("stair1_",))
```

- Darker floors read better in plan than light ones.
- Avoid grey bands and black borders around the plan. An owner could not read a plan with them.
- For a white surround, add a white emission box under the floor in plan views only:
  `box("ground_plan", x0 - 20, x1 + 20, y0 - 20, y1 + 20, -0.31, -0.30, emission("ground", (1, 1, 1), 1.0))`.

## Plan-only overlays

Draw overlays as thin flat objects just under the cut, and create them only when the view is a plan.

- `dotted_square`: an existing post.
- `dotted_rect`: a wall to be removed.
- `dashed_path`: the outline of the floor above. Close it by repeating the first point.
- `door_swings`: swing arcs from the extracted plan.

## Labels, rulers, and scale

- Add labels after the render with PIL, not as 3D text.
- `project_points(points)` returns pixel positions for world points in the current camera. Write them to JSON for the PIL pass.
- `annotate_plan.py IN.png OUT.png CALLOUTS.json` draws circled callouts. CALLOUTS.json uses the plan view's `center` and `width`, in project units.
- Put a ruler in project units on a plan view when someone will read dimensions off it.
- Put scale props in perspectives.
