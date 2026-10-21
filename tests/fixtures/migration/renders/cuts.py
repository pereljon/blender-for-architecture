"""Cut list for the invented kitchen top in the migration fixture: pieces in millimetres on one stock board."""

STOCK = (3000, 1200)
KERF = 4
PIECES = [
    ("A", 1800, 650),
    ("B", 1100, 650),
    ("C", 800, 450),
    ("D", 1200, 300),
    ("E", 600, 300),
]


def place_pieces():
    """Shelf-pack the pieces left to right, tallest first; returns (name, x, y, w, h) with offsets in mm."""
    out, x, y, row_h = [], 0, 0, 0
    for name, w, h in sorted(PIECES, key=lambda p: -p[2]):
        if x + w > STOCK[0]:
            x, y, row_h = 0, y + row_h + KERF, 0
        out.append((name, x, y, w, h))
        x += w + KERF
        row_h = max(row_h, h)
    return out
