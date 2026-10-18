"""Extract wall rectangles, door swings and door leaves from an architect's plan PDF (vector linework) into JSON.

Usage (PyMuPDF via uvx; nothing installed system-wide):
  uvx --with pymupdf python -I blender/lib/extract_plan.py CONFIG.json

CONFIG.json holds everything that belongs to one drawing set (see DEFAULTS below and plan_config.example.json).
Values are in PDF points unless named otherwise. Find them by listing page.get_drawings() for a small area and
reading the fill, stroke colour and width of known walls, doors and posts; every office draws them differently.

Output coordinates are project units (feet at pt_per_unit = 9.0 for a 1/8" = 1'-0" sheet): X to the right from
origin[0], Y up the sheet from origin[1]. Run it again whenever a new plan set arrives.

How the walls are found (tune the thresholds per drawing set):
- New walls: rectangles with a gray fill (new_fill). Parts hidden by clipping paths where doors cut them are
  split into the runs the rendered sheet actually shows (room fill or paper at a sample point means an opening).
- Existing walls: pairs of parallel black lines (existing_width) pair_gap apart.
- Posts: solid black filled rectangles at least post_min across. Filled triangles (section arrows) are skipped.
- Excluded: dashed property lines (property_y), anything right of exclude_x_min (a wall the model rebuilds itself),
  isolated fragments in doorways ("phantom dots"), and short pieces that touch no other wall.
Extraction misses angled walls and some outside walls. Add those in the build script's correction layer
(EXTRA_WALLS, WALL_FIXES, WALL_REPLACE), never by editing the JSON.

Several sheets: give each its own entry in "sheets" with a shift that registers it onto the first sheet's frame
(match a feature drawn on both, such as lot-line posts). Do not reuse one sheet's offset for a drawing from another
source; register each source separately.
"""
import json
import math
import os
import sys

import pymupdf

DEFAULTS = dict(
    pt_per_unit=9.0,              # 1/8" = 1'-0" -> 9 pt per foot
    origin=[0.0, 0.0],            # PDF x of the plan's X = 0 line, PDF y of the Y = 0 line
    new_fill=0.754,               # gray fill of new walls
    existing_width=[1.15, 1.5],   # stroke width range of existing-wall lines
    pair_gap=[2.0, 8.5],          # distance between the two lines of an existing wall
    post_min=2.0,                 # smallest solid black rectangle counted as a post
    swing_width=0.24,             # stroke width of door swing arcs
    leaf_width=0.48,              # stroke width of door leaves and sliding panels
    leaf_gap=[0.9, 1.7],          # leaf thickness (two parallel lines)
    leaf_len=[8.0, 29.0],
    min_piece=[4.0, 7.2],         # shortest kept piece: new, existing (drops jamb fragments)
    exclude_x_min=None,           # drop walls right of this PDF x (a wall rebuilt in the model)
    anchor_y=None,                # PDF y of a known wall face: short pieces reaching it are kept
    leaf_exclude=[],              # [x0, y0, x1, y1] zones whose parallel lines are not doors (stair treads)
)
CFG = dict(DEFAULTS)
REGION = None
PROPERTY_Y = ()


def inside(r):
    return r[0] >= REGION[0] - 1 and r[2] <= REGION[2] and r[1] >= REGION[1] and r[3] <= REGION[3]


def visible_runs(pix, r, zoom, step=0.25):
    """Split a gray wall rectangle into the runs the rendered sheet actually shows.

    A sample point counts as wall unless it renders as room fill (light blue) or white paper. Short gaps
    (dimension ticks, text) are bridged; runs shorter than 2.5 pt
    (1 pt for short stubs) are dropped.
    """
    x0, y0, x1, y1 = r
    horiz = x1 - x0 >= y1 - y0
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    c = (y0 + y1) / 2 if horiz else (x0 + x1) / 2
    flags = []
    t = a0 + step / 2
    while t < a1:
        x, y = (t, c) if horiz else (c, t)
        px = pix.pixel(int(x * zoom), int(y * zoom))
        blue = px[2] > 235 and px[0] < 225
        paper = min(px[:3]) > 245
        flags.append((t, not (blue or paper)))
        t += step
    runs, cur = [], None
    for t, on in flags:
        if on:
            cur = [t, t] if cur is None else [cur[0], t]
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    merged = []
    for r0, r1 in runs:
        if merged and r0 - merged[-1][1] < 1.5:
            merged[-1][1] = r1
        else:
            merged.append([r0, r1])
    out = []
    for r0, r1 in merged:
        r0, r1 = max(a0, r0 - step / 2), min(a1, r1 + step / 2)
        # drop slivers left by dimension ticks crossing a hidden wall; keep short jamb stubs
        if r1 - r0 >= (2.5 if a1 - a0 > 20 else 1.0):
            out.append((r0, y0, r1, y1) if horiz else (x0, r0, x1, r1))
    return out


def remove_overlaps(walls):
    """Cut each wall where an earlier wall already occupies the same footprint.

    Overlapping boxes render black in Cycles (shading points inside another solid). New walls come first,
    so an existing-wall pair that runs through a new wall is trimmed to the parts outside it.
    """
    done = []
    for kind, r in walls:
        pieces = [r]
        for _, q in done:
            nxt = []
            for p in pieces:
                ix0, iy0 = max(p[0], q[0]), max(p[1], q[1])
                ix1, iy1 = min(p[2], q[2]), min(p[3], q[3])
                if ix1 - ix0 <= 0.05 or iy1 - iy0 <= 0.05:
                    nxt.append(p)
                    continue
                horiz = p[2] - p[0] >= p[3] - p[1]
                if horiz:
                    if p[0] < ix0 - 0.05:
                        nxt.append((p[0], p[1], ix0, p[3]))
                    if ix1 < p[2] - 0.05:
                        nxt.append((ix1, p[1], p[2], p[3]))
                else:
                    if p[1] < iy0 - 0.05:
                        nxt.append((p[0], p[1], p[2], iy0))
                    if iy1 < p[3] - 0.05:
                        nxt.append((p[0], iy1, p[2], p[3]))
            pieces = nxt
        done += [(kind, p) for p in pieces if max(p[2] - p[0], p[3] - p[1]) >= 0.8]
    return done


def door_swings(page):
    """Door swing arcs: chains of short 0.24 pt line segments turning through about 90 degrees.

    Returns [(arc_points, leaf)] in PDF points; leaf is the line from the hinge to the open end when the sheet
    draws one (any line ending at an arc end with a length close to the radius), else None.
    """
    segs, lines = [], []
    for d in page.get_drawings():
        r = d["rect"]
        if not inside(tuple(r)):
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = (it[1].x, it[1].y), (it[2].x, it[2].y)
            L = math.dist(a, b)
            lines.append((a, b, L))
            if abs((d.get("width") or 0) - CFG["swing_width"]) < 0.02 and 0.8 < L < 7 and d.get("color") == (0.0, 0.0, 0.0):
                segs.append((a, b))
    key = lambda q: (round(q[0], 1), round(q[1], 1))
    adj = {}
    for i, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append(i)
        adj.setdefault(key(b), []).append(i)
    used, out = set(), []
    for i in range(len(segs)):
        if i in used:
            continue
        chain = [segs[i][0], segs[i][1]]
        used.add(i)
        for end in (1, 0):                       # grow at the tail, then at the head
            while True:
                q = chain[-1] if end else chain[0]
                nxt = [j for j in adj.get(key(q), []) if j not in used]
                if len(nxt) != 1:
                    break
                j = nxt[0]
                used.add(j)
                a, b = segs[j]
                p2 = b if key(a) == key(q) else a
                chain.append(p2) if end else chain.insert(0, p2)
        hs = [math.atan2(q2[1] - q1[1], q2[0] - q1[0]) for q1, q2 in zip(chain, chain[1:])]
        dh = [(h2 - h1 + math.pi) % (2 * math.pi) - math.pi for h1, h2 in zip(hs, hs[1:])]
        kinks = [k for k, v in enumerate(dh) if abs(v) > 0.6]   # jamb ticks joined to the arc: cut them off
        if kinks:
            parts, start = [], 0
            for k in kinks + [len(hs) - 1]:
                parts.append(chain[start:k + 2])
                start = k + 1
            chain = max(parts, key=len)
        if len(chain) < 5:
            continue
        a, b = chain[0], chain[-1]
        hs = [math.atan2(q2[1] - q1[1], q2[0] - q1[0]) for q1, q2 in zip(chain, chain[1:])]
        turn = abs(sum((h2 - h1 + math.pi) % (2 * math.pi) - math.pi for h1, h2 in zip(hs, hs[1:])))
        chord = math.dist(a, b)
        if not (0.45 < turn < 1.9 and 10 < chord < 50):     # half arcs occur where a swing is split
            continue
        rad = chord / math.sqrt(2)
        leaf = None
        for la, lb, L in lines:
            if abs(L - rad) > 0.25 * rad:
                continue
            for e in (a, b):
                if math.dist(la, e) < 0.8 or math.dist(lb, e) < 0.8:
                    leaf = (la, lb)
        out.append((chain, leaf))
    return out


def door_leaves(page):
    """Door leaves and sliding panels: two parallel 0.48 pt black lines 0.9 to 1.7 pt apart, 8 to 29 pt long.

    Covers swing-door leaves drawn open, bifold panels, pocket-door panels and bypass sliders. A pair with a third
    parallel line close by is a fixture outline (sinks are drawn with three lines) and is skipped.
    Returns [(a, b, thickness)] in PDF points: the leaf's centre line and its thickness.
    """
    ls = []
    for d in page.get_drawings():
        if not inside(tuple(d["rect"])) or abs((d.get("width") or 0) - CFG["leaf_width"]) > 0.02 or d.get("color") != (0.0, 0.0, 0.0):
            continue
        for it in d["items"]:
            if it[0] == "l":
                a, b = (it[1].x, it[1].y), (it[2].x, it[2].y)
                xm = CFG["exclude_x_min"]
                if CFG["leaf_len"][0] <= math.dist(a, b) <= CFG["leaf_len"][1] and (xm is None or min(a[0], b[0]) < xm):
                    ls.append((a, b) if a < b else (b, a))
    ls = sorted(set((tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in b)) for a, b in ls))
    def near(line, a, u, L):
        """True if line is parallel to the leaf line (a, u, L), within 2.7 pt of it and overlapping it."""
        c, e = line
        M = math.dist(c, e)
        v = ((e[0] - c[0]) / M, (e[1] - c[1]) / M)
        if abs(u[0] * v[1] - u[1] * v[0]) > 0.03:
            return False
        gap = abs((c[0] - a[0]) * u[1] - (c[1] - a[1]) * u[0])
        s0, s1 = sorted(((c[0] - a[0]) * u[0] + (c[1] - a[1]) * u[1], (e[0] - a[0]) * u[0] + (e[1] - a[1]) * u[1]))
        return gap <= 2.7 and min(L, s1) - max(0.0, s0) > 0.5 * min(L, M)

    out, used = [], set()
    for i, (a, b) in enumerate(ls):
        if i in used:
            continue
        L = math.dist(a, b)
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        for j in range(i + 1, len(ls)):
            if j in used:
                continue
            c, e = ls[j]
            M = math.dist(c, e)
            v = ((e[0] - c[0]) / M, (e[1] - c[1]) / M)
            if abs(u[0] * v[1] - u[1] * v[0]) > 0.03:              # not parallel
                continue
            gap = abs((c[0] - a[0]) * u[1] - (c[1] - a[1]) * u[0])  # perpendicular distance
            s0, s1 = sorted(((c[0] - a[0]) * u[0] + (c[1] - a[1]) * u[1], (e[0] - a[0]) * u[0] + (e[1] - a[1]) * u[1]))
            overlap = min(L, s1) - max(0.0, s0)
            if CFG["leaf_gap"][0] <= gap <= CFG["leaf_gap"][1] and overlap >= 0.8 * min(L, M):
                used.update((i, j))
                if any(near(ls[k], a, u, L) for k in range(len(ls)) if k not in (i, j)):
                    break
                mid = lambda p, q: ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                ca = (a[0] + u[0] * max(0.0, s0), a[1] + u[1] * max(0.0, s0))
                cb = (a[0] + u[0] * min(L, s1), a[1] + u[1] * min(L, s1))
                n = (-u[1] * gap / 2, u[0] * gap / 2)
                side = 1 if (c[0] - a[0]) * n[0] + (c[1] - a[1]) * n[1] > 0 else -1
                pa = (ca[0] + side * n[0], ca[1] + side * n[1])
                pb = (cb[0] + side * n[0], cb[1] + side * n[1])
                cx = (pa[0] + pb[0]) / 2
                cy = (pa[1] + pb[1]) / 2
                if not any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] for z in CFG["leaf_exclude"]):
                    out.append((pa, pb, gap))
                break
    return out


def main():
    with open(sys.argv[1]) as fh:
        cfg = json.load(fh)
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    CFG.update({k: v for k, v in cfg.items() if k != "sheets"})
    for sh in cfg["sheets"]:
        extract(os.path.join(base, cfg["pdf"]), sh["page"], tuple(sh["region"]), tuple(sh.get("shift", (0.0, 0.0))),
                os.path.join(base, sh["out"]), tuple(sh.get("property_y", ())), sh.get("keep_x_max", False))


def extract(pdf, page_no, region, shift, out_path, property_y=(), keep_x_max=False):
    """keep_x_max=True keeps walls right of exclude_x_min on this sheet (a sheet where that wall is not rebuilt)."""
    global REGION, PROPERTY_Y
    REGION = region
    PROPERTY_Y = property_y
    PT_FT = CFG["pt_per_unit"]
    X_ORIGIN, Y_ORIGIN = CFG["origin"]
    page = pymupdf.open(pdf)[page_no]
    zoom = 6
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    new, segs, posts = [], [], []
    for p in page.get_drawings():
        rect = tuple(p["rect"])
        if not inside(rect):
            continue
        fill, color, width = p.get("fill"), p.get("color"), p.get("width") or 0
        if fill and abs(fill[0] - CFG["new_fill"]) < 0.01:
            for it in p["items"]:
                if it[0] == "re":
                    r = it[1]
                    if min(r.x1 - r.x0, r.y1 - r.y0) >= 1.5:
                        new.extend(visible_runs(pix, (r.x0, r.y0, r.x1, r.y1), zoom))
        elif (fill == (0.0, 0.0, 0.0) and min(rect[2] - rect[0], rect[3] - rect[1]) >= CFG["post_min"]
              and any(it[0] == "re" for it in p["items"])):
            posts.append(rect)                      # solid black rectangle: existing post
        elif color == (0.0, 0.0, 0.0) and CFG["existing_width"][0] <= width < CFG["existing_width"][1] and fill is None:
            for it in p["items"]:
                if it[0] != "l":
                    continue
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.2 and abs(a.x - b.x) > 2:
                    y = (a.y + b.y) / 2
                    if any(abs(y - py) < 0.3 for py in PROPERTY_Y):
                        continue
                    segs.append(("h", min(a.x, b.x), max(a.x, b.x), y))
                elif abs(a.x - b.x) < 0.2 and abs(a.y - b.y) > 2:
                    segs.append(("v", min(a.y, b.y), max(a.y, b.y), (a.x + b.x) / 2))

    existing = []
    for o in "hv":
        group = [s for s in segs if s[0] == o]
        for s in group:
            best = None
            for t in group:
                gap = t[3] - s[3]
                if CFG["pair_gap"][0] <= gap <= CFG["pair_gap"][1]:
                    lo, hi = max(s[1], t[1]), min(s[2], t[2])
                    # prefer the partner line with the longest overlap, then the smallest gap
                    if hi - lo > 3 and (best is None or (hi - lo, -gap) > (best[2] - best[1], -best[0])):
                        best = (gap, lo, hi, t)
            if best:
                gap, lo, hi, t = best
                existing.append((lo, s[3], hi, t[3]) if o == "h" else (s[3], lo, t[3], hi))


    def covered(r, pool):
        return any(r[0] >= q[0] - 0.5 and r[2] <= q[2] + 0.5 and r[1] >= q[1] - 0.5 and r[3] <= q[3] + 0.5
                   for q in pool if q is not r)

    walls = []
    for kind, r in [("new", r) for r in new] + [("existing", r) for r in existing]:
        if kind == "existing" and covered(r, new):
            continue
        if not keep_x_max and CFG["exclude_x_min"] is not None and r[0] >= CFG["exclude_x_min"]:
            continue
        if any(max(abs(r[i] - q[i]) for i in range(4)) < 0.3 for _, q in walls):
            continue
        walls.append((kind, r))

    walls += [("post", r) for r in posts]
    walls = remove_overlaps(walls)
    # drop jamb fragments left in doorways (phantom dots): tiny pieces that are not posts
    walls = [(k, r) for k, r in walls
             if k == "post" or max(r[2] - r[0], r[3] - r[1]) >= CFG["min_piece"][0 if k == "new" else 1]]
    # and pieces under 1 ft that touch no other wall (gray wall left visible under a dimension tick)
    touch = lambda r, q: r[0] <= q[2] + 0.5 and q[0] <= r[2] + 0.5 and r[1] <= q[3] + 0.5 and q[1] <= r[3] + 0.5
    anchor = CFG["anchor_y"]                    # a known wall face that is not extracted: pieces reaching it stay
    walls = [(k, r) for k, r in walls
             if max(r[2] - r[0], r[3] - r[1]) >= PT_FT or (anchor is not None and r[1] <= anchor)
             or any(q is not r and touch(r, q) for _, q in walls)]
    sx, sy = shift
    out = []
    for kind, (x0, y0, x1, y1) in walls:
        out.append(dict(kind=kind,
                        x0=round((x0 - sx - X_ORIGIN) / PT_FT, 4), x1=round((x1 - sx - X_ORIGIN) / PT_FT, 4),
                        y0=round((Y_ORIGIN - (y1 - sy)) / PT_FT, 4), y1=round((Y_ORIGIN - (y0 - sy)) / PT_FT, 4)))
    ft = lambda q: [round((q[0] - sx - X_ORIGIN) / PT_FT, 3), round((Y_ORIGIN - (q[1] - sy)) / PT_FT, 3)]
    doors = [dict(arc=[ft(q) for q in arc], leaf=[ft(q) for q in leaf] if leaf else None)
             for arc, leaf in door_swings(page)]
    leaves = [dict(a=ft(a), b=ft(b), t=round(t / PT_FT, 3)) for a, b, t in door_leaves(page)]
    with open(out_path, "w") as fh:
        json.dump(dict(source=os.path.basename(pdf), page=page_no, units="plan units", walls=out, doors=doors, leaves=leaves),
                  fh, indent=1)
    print(f"{len(out)} walls ({sum(w['kind'] == 'new' for w in out)} new), {len(doors)} door swings "
          f"({sum(d['leaf'] is not None for d in doors)} with leaf), {len(leaves)} leaves and panels -> {out_path}")


if __name__ == "__main__":
    main()
