"""Wall rectangles that almost meet, and door-sized openings between in-line walls (plain Python, no Blender needed).

Rects are (x0, x1, y0, y1) or (x0, x1, y0, y1, z0, z1) tuples, or dicts with x0, x1, y0, y1 and optional z0, z1
(load_plan walls). unit is metres per rect unit; gap, opening and touch are metres. Lengths returned are metres.
"""
import math


def _norm(r, unit):
    if isinstance(r, dict):
        v = [r.get(k) for k in ("x0", "x1", "y0", "y1", "z0", "z1")]
    else:
        v = list(r[:6]) + [None] * (6 - len(r[:6]))
        if len(r) < 6:
            v[4] = v[5] = None
    v = [None if q is None else q * unit for q in v]
    x0, x1, y0, y1, z0, z1 = v
    z = None if z0 is None or z1 is None else (min(z0, z1), max(z0, z1))
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z


def _same_level(a, b, touch):
    return a[4] is None or b[4] is None or min(a[4][1], b[4][1]) - max(a[4][0], b[4][0]) > touch


def _along_x(r):
    return r[1] - r[0] >= r[3] - r[2]


def _thickness(r):
    return min(r[1] - r[0], r[3] - r[2])


def _subtract(r, h):
    a0, a1, b0, b1 = r
    h0, h1, k0, k1 = max(h[0], a0), min(h[1], a1), max(h[2], b0), min(h[3], b1)
    if h0 >= h1 or k0 >= k1:
        return [r]
    out = []
    if k0 > b0:
        out.append((a0, a1, b0, k0))
    if k1 < b1:
        out.append((a0, a1, k1, b1))
    if h0 > a0:
        out.append((a0, h0, k0, k1))
    if h1 < a1:
        out.append((h1, a1, k0, k1))
    return out


def _left_over(region, fills):
    """Area of region (x0, x1, y0, y1) that no rect in fills covers."""
    parts = [region]
    for f in fills:
        parts = [q for p in parts for q in _subtract(p, f[:4])]
    return sum((p[1] - p[0]) * (p[3] - p[2]) for p in parts)


def _overlaps(a, b):
    return min(a[1], b[1]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[2], b[2])


def wall_gaps(rects, unit=1.0, gap=0.3, touch=0.001):
    """Hits (i, j, kind, length_m) between rects i < j (input order) that almost meet.

    kind "gap": the rects are apart by more than touch and at most gap, with nothing filling the space between.
    kind "corner": the rects touch but leave part of their junction square unfilled (corner point, partial butt,
    jog); length is the contact length. A third rect that fills the space or the junction clears the hit.
    Only rects on one level (overlapping z ranges, or no z range) are compared or count as filling.
    """
    rs = [_norm(r, unit) for r in rects]
    hits = []
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i], rs[j]
            if not _same_level(a, b, touch):
                continue
            ox, oy = _overlaps(a[:4], b[:4])
            d = math.hypot(max(0.0, -ox), max(0.0, -oy))
            fills = [c for c in rs if _same_level(c, a, touch) and _same_level(c, b, touch)]
            if touch < d <= gap:
                spans = []
                for lo0, lo1, hi0, hi1, o in ((a[0], b[0], a[1], b[1], ox), (a[2], b[2], a[3], b[3], oy)):
                    spans.append((max(lo0, lo1), min(hi0, hi1)) if o >= 0 else (min(hi0, hi1), max(lo0, lo1)))
                region = (*spans[0], *spans[1])
                thin = region[1] - region[0] <= touch or region[3] - region[2] <= touch
                if thin or _left_over(region, fills) >= touch * touch:
                    hits.append((i, j, "gap", d))
            elif d <= touch and not (ox > touch and oy > touch):
                c = max(0.0, ox, oy)
                if c >= min(_thickness(a), _thickness(b)) - touch:
                    continue
                if _along_x(a) != _along_x(b):
                    vert = b if _along_x(a) else a
                    horiz = a if _along_x(a) else b
                    region = (vert[0], vert[1], horiz[2], horiz[3])
                else:
                    k = 0 if _along_x(a) else 1
                    t = k if (ox, oy)[k] <= touch else 1 - k
                    u = 1 - t
                    half = min(_thickness(a), _thickness(b)) / 2
                    line = (min(a[2 * t + 1], b[2 * t + 1]) + max(a[2 * t], b[2 * t])) / 2
                    span_u = (min(a[2 * u], b[2 * u]), max(a[2 * u + 1], b[2 * u + 1]))
                    region = (line - half, line + half, *span_u) if t == 0 else (*span_u, line - half, line + half)
                if _left_over(region, fills) >= touch * touch:
                    hits.append((i, j, "corner", c))
    return hits


def wall_openings(rects, unit=1.0, gap=0.3, opening=2.5, touch=0.001):
    """Door-sized openings (i, j, width_m, (x0, x1, y0, y1)) between in-line rects i < j; the box is in metres.

    A pair qualifies when both run the same way, their thickness bands overlap by more than half the thinner
    thickness, and the separation along the run is above gap and at most opening. A rect on the level of both
    that covers part of the box (a crossing wall, a header drawn as a wall) clears the opening.
    """
    rs = [_norm(r, unit) for r in rects]
    out = []
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            a, b = rs[i], rs[j]
            if not _same_level(a, b, touch) or _along_x(a) != _along_x(b):
                continue
            k = 0 if _along_x(a) else 2
            across = 2 - k
            band = min(a[across + 1], b[across + 1]) - max(a[across], b[across])
            if band <= min(_thickness(a), _thickness(b)) / 2:
                continue
            w = max(a[k], b[k]) - min(a[k + 1], b[k + 1])
            if not gap < w <= opening:
                continue
            run = (min(a[k + 1], b[k + 1]), max(a[k], b[k]))
            cross = (max(a[across], b[across]), min(a[across + 1], b[across + 1]))
            box = (*run, *cross) if k == 0 else (*cross, *run)
            blocked = False
            for c in rs:
                if c is a or c is b or not (_same_level(c, a, touch) and _same_level(c, b, touch)):
                    continue
                cx, cy = _overlaps(box, c[:4])
                if cx > touch and cy > touch:
                    blocked = True
                    break
            if not blocked:
                out.append((i, j, w, box))
    return out
