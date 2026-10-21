"""Seeded defect for the template: adds a box 0.11 m above the floor and runs the template's main().

Copy this file beside scene_template.py. run_checks must fail on floor_fit, so the run exits non-zero without a DONE line.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import scene_template as st

_build = st.build


def build(opts):
    _build(opts)
    st.box("float_test", 2.0, 2.4, 3.0, 3.4, 0.11, 0.9)


st.build = build
sys.argv = [sys.argv[0], "--", "--view", "persp", "--res", "160", "--samples", "8",
            "--out", os.path.join(HERE, "seeded.png")]
st.main()
