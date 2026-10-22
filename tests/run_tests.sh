#!/bin/bash
# Runs every test for the blender-for-architecture skill headless. Exits non-zero on any failure.
# Output goes to tests/out/. Override BLENDER or SCRIPTS_DIR (default: ../scripts) from the environment.
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="$(dirname "$HERE")"
OUT="$HERE/out"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
SCRIPTS_DIR="${SCRIPTS_DIR:-$SKILL/scripts}"
export SCRIPTS_DIR
mkdir -p "$OUT"

TO="$(command -v timeout || command -v gtimeout || true)"
FAILED=()
PASSED=()

# with_timeout SECONDS CMD...: GNU timeout when present, else the Python runner.
with_timeout() {
    local secs="$1"; shift
    if [ -n "$TO" ]; then
        "$TO" "$secs" "$@"
    else
        python3 -I "$HERE/with_timeout.py" "$secs" "$@"
    fi
}

# step NAME SECONDS CMD...: runs one step, logs to out/NAME.log, records pass or fail.
step() {
    local name="$1" secs="$2"; shift 2
    if with_timeout "$secs" "$@" >"$OUT/$name.log" 2>&1; then
        PASSED+=("$name"); echo "PASS $name"
    else
        local rc=$?
        FAILED+=("$name"); echo "FAIL $name (exit $rc, log $OUT/$name.log)"
        tail -n 15 "$OUT/$name.log" | sed 's/^/    /'
    fi
}

# expect_line NAME LOG PATTERN: passes when the log has a line matching the grep pattern.
expect_line() {
    if grep -Eq "$3" "$2"; then
        PASSED+=("$1"); echo "PASS $1"
    else
        FAILED+=("$1"); echo "FAIL $1 (no line matching '$3' in $2)"
    fi
}

# expect_order NAME LOG FIRST SECOND: passes when a line matching FIRST comes before the first line matching SECOND.
expect_order() {
    local a b
    a="$(grep -En "$3" "$2" | head -n 1 | cut -d: -f1)"
    b="$(grep -En "$4" "$2" | head -n 1 | cut -d: -f1)"
    if [ -n "$a" ] && [ -n "$b" ] && [ "$a" -lt "$b" ]; then
        PASSED+=("$1"); echo "PASS $1"
    else
        FAILED+=("$1"); echo "FAIL $1 (no line matching '$3' before a line matching '$4' in $2)"
    fi
}

# expect_no_line NAME LOG PATTERN: passes when no line of the log matches the grep pattern.
expect_no_line() {
    if grep -Eq "$3" "$2"; then
        FAILED+=("$1"); echo "FAIL $1 (unexpected line matching '$3' in $2)"
    else
        PASSED+=("$1"); echo "PASS $1"
    fi
}

# step_fails NAME SECONDS CMD...: runs one step that must exit non-zero; a timeout (124) does not count.
step_fails() {
    local name="$1" secs="$2"; shift 2
    with_timeout "$secs" "$@" >"$OUT/$name.log" 2>&1
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        FAILED+=("$name"); echo "FAIL $name (exit 0, expected non-zero, log $OUT/$name.log)"
    elif [ "$rc" -eq 124 ]; then
        FAILED+=("$name"); echo "FAIL $name (timeout, log $OUT/$name.log)"
    else
        PASSED+=("$name"); echo "PASS $name (exit $rc)"
    fi
}

blender_test() {
    local name="$1"; shift
    step "$name" 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$HERE/$name.py" -- "$@"
    expect_line "$name:finished" "$OUT/$name.log" "^TESTPASS $name\$"
}

# 0. syntax and prerequisites
step syntax:bash 30 bash -n "$HERE/run_tests.sh"
step syntax:python 60 python3 -I -m py_compile "$HERE"/tcommon.py "$HERE"/bl_*.py "$HERE"/test_*.py \
    "$HERE"/check_png.py "$HERE"/list_views.py "$HERE"/template_lib.py "$HERE"/with_timeout.py "$HERE"/seed_template.py
rm -rf "$HERE/__pycache__"

missing=0
for f in bhelpers.py mannequin.py checks.py wall_gaps.py ifc_walls.py sheets.py compose.py annotate_plan.py extract_plan.py; do
    [ -f "$SCRIPTS_DIR/$f" ] || { echo "MISSING $SCRIPTS_DIR/$f"; missing=1; }
done
[ -f "$SKILL/templates/scene_template.py" ] || { echo "MISSING $SKILL/templates/scene_template.py"; missing=1; }
[ -x "$BLENDER" ] || { echo "MISSING Blender at $BLENDER"; missing=1; }
command -v uvx >/dev/null || { echo "MISSING uvx"; missing=1; }
if [ "$missing" = 1 ]; then
    FAILED+=("prerequisites")
    echo "Cannot run the suite: prerequisites missing."
    exit 1
fi

# 1. Blender tests
blender_test bl_helpers
blender_test bl_mannequin
blender_test bl_checks
blender_test bl_render
blender_test bl_rev2
blender_test bl_rev3
blender_test bl_rev4
blender_test bl_rev6
blender_test bl_v110
blender_test bl_v111
blender_test bl_extensions
SKIPS=""
SKIP_LINE="$(grep -m1 '^SKIP' "$OUT/bl_extensions.log")"
if [ -n "$SKIP_LINE" ]; then
    echo "$SKIP_LINE"
    SKIPS=" (1 skipped: bl_extensions: ${SKIP_LINE#SKIP })"
fi
expect_line bl_render:DONE-persp "$OUT/bl_render.log" "^DONE $OUT/render_persp.png\$"
expect_line bl_render:DONE-plan "$OUT/bl_render.log" "^DONE $OUT/render_plan.png\$"

# 2. Template renders, run the way a project would: template beside a lib/ copy of scripts/
TPL="$OUT/tpl"
rm -rf "$TPL"; mkdir -p "$TPL"
cp "$SKILL/templates/scene_template.py" "$TPL/scene_template.py"
LIB="$(python3 -I "$HERE/template_lib.py" "$SKILL/templates/scene_template.py")"
if [ -z "$LIB" ]; then
    FAILED+=("template:lib"); echo "FAIL template:lib (the template has no module-level LIB)"
    cp -R "$SCRIPTS_DIR" "$TPL/lib"
else
    PASSED+=("template:lib"); echo "PASS template:lib ($LIB)"
    mkdir -p "$TPL/lib"
    cp -R "$SCRIPTS_DIR" "$TPL/lib/$LIB"
fi
VIEWS="$(python3 -I "$HERE/list_views.py" "$TPL/scene_template.py")"
if [ -z "$VIEWS" ]; then
    FAILED+=("template:views"); echo "FAIL template:views (no VIEWS keys found)"
elif [ "$(echo "$VIEWS" | wc -l | tr -d ' ')" -lt 2 ]; then
    FAILED+=("template:views"); echo "FAIL template:views (expected a perspective and a plan entry)"
fi
for v in $VIEWS; do
    img="$TPL/$v.png"
    step "template:$v" 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$TPL/scene_template.py" -- \
        --view "$v" --res 160 --samples 8 --out "$img"
    expect_line "template:$v:DONE" "$OUT/template:$v.log" "^DONE $img\$"
    expect_order "template:$v:checks" "$OUT/template:$v.log" "^OK run_checks\$" "^DONE $img\$"
    step "template:$v:image" 120 uvx --with pillow python -I "$HERE/check_png.py" "$img" 160
done

# 2a. A floating box in the template scene stops the render: run_checks fails and no DONE line is written
cp "$HERE/seed_template.py" "$TPL/seed_template.py"
step_fails template:seeded-defect 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$TPL/seed_template.py"
expect_line template:seeded-defect:FAIL "$OUT/template:seeded-defect.log" "^FAIL run_checks: floor_fit\$"
expect_no_line template:seeded-defect:no-DONE "$OUT/template:seeded-defect.log" "^DONE "

# 2b. Template --export-pieces writes valid JSON and prints DONE without rendering
PJ="$TPL/pieces.json"
step template:export-pieces 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$TPL/scene_template.py" -- \
    --export-pieces "$PJ"
expect_line template:export-pieces:DONE "$OUT/template:export-pieces.log" "^DONE $PJ\$"
step template:export-pieces:json 60 python3 -I -c \
    'import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d["pieces"], list)' "$PJ"

# 2c. The template beside a flat lib/ copy (no version folder) stops on the missing import and writes no image
FLAT="$OUT/tpl_flat"
rm -rf "$FLAT"; mkdir -p "$FLAT"
cp "$SKILL/templates/scene_template.py" "$FLAT/scene_template.py"
cp -R "$SCRIPTS_DIR" "$FLAT/lib"
step_fails template:flat-lib 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$FLAT/scene_template.py" -- \
    --view persp --res 160 --samples 8 --out "$FLAT/flat.png"
expect_line template:flat-lib:ModuleNotFoundError "$OUT/template:flat-lib.log" "ModuleNotFoundError"
expect_no_line template:flat-lib:no-DONE "$OUT/template:flat-lib.log" "^DONE "

# 2d. The synthetic monolithic project of eval E10 renders, and its sheet generator runs the way the project ran it
FIX="$HERE/fixtures/migration"
step fixture:render 420 "$BLENDER" --factory-startup -b --python-exit-code 1 -P "$FIX/renders/build_house.py" -- \
    --view living --res 160 --samples 8 --out "$OUT/fixture/living.png"
expect_line fixture:render:DONE "$OUT/fixture:render.log" "^DONE $OUT/fixture/living.png\$"
step fixture:sheet 120 uvx --with pillow python "$FIX/renders/make_sheet.py" "$OUT/fixture/sheet.png"
step_fails fixture:sheet-isolated 120 uvx --with pillow python -I "$FIX/renders/make_sheet.py" "$OUT/fixture/sheet_isolated.png"
expect_line fixture:sheet-isolated:ModuleNotFoundError "$OUT/fixture:sheet-isolated.log" "ModuleNotFoundError"
rm -rf "$FIX/renders/__pycache__"

# 3. Plain Python tests (after the renders, which feed compose and annotate)
step test_sheets 300 uvx --with pillow python -I "$HERE/test_sheets.py"
expect_line test_sheets:finished "$OUT/test_sheets.log" "^TESTPASS test_sheets\$"
step test_compose 300 uvx --with pillow python -I "$HERE/test_compose.py"
expect_line test_compose:finished "$OUT/test_compose.log" "^TESTPASS test_compose\$"
step test_rev3 120 uvx --with pillow python -I "$HERE/test_rev3.py"
expect_line test_rev3:finished "$OUT/test_rev3.log" "^TESTPASS test_rev3\$"
step test_extract 300 uvx --with pillow --with pymupdf python -I "$HERE/test_extract.py"
expect_line test_extract:finished "$OUT/test_extract.log" "^TESTPASS test_extract\$"
step test_wall_gaps 60 python3 -I "$HERE/test_wall_gaps.py"
expect_line test_wall_gaps:finished "$OUT/test_wall_gaps.log" "^TESTPASS test_wall_gaps\$"
step test_api_doc 60 python3 -I "$HERE/test_api_doc.py"
expect_line test_api_doc:finished "$OUT/test_api_doc.log" "^TESTPASS test_api_doc\$"
step test_ifc_walls 60 python3 -I "$HERE/test_ifc_walls.py"
expect_line test_ifc_walls:finished "$OUT/test_ifc_walls.log" "^TESTPASS test_ifc_walls\$"
step test_description 60 python3 -I "$HERE/test_description.py"
expect_line test_description:finished "$OUT/test_description.log" "^TESTPASS test_description\$"
step test_extensions_doc 60 python3 -I "$HERE/test_extensions_doc.py"
expect_line test_extensions_doc:finished "$OUT/test_extensions_doc.log" "^TESTPASS test_extensions_doc\$"
step test_v110 120 python3 -I "$HERE/test_v110.py"
expect_line test_v110:finished "$OUT/test_v110.log" "^TESTPASS test_v110\$"
step test_v111 60 python3 -I "$HERE/test_v111.py"
expect_line test_v111:finished "$OUT/test_v111.log" "^TESTPASS test_v111\$"
SKIP_LINES="$(grep -h '^SKIP' "$OUT/test_v110.log" "$OUT/bl_v110.log" 2>/dev/null)"
if [ -n "$SKIP_LINES" ]; then
    echo "$SKIP_LINES"
    SKIPS="$SKIPS (v1.1.0 tests: $(echo "$SKIP_LINES" | wc -l | tr -d ' ') skipped)"
fi

echo
echo "${#PASSED[@]} passed, ${#FAILED[@]} failed$SKIPS"
if [ "${#FAILED[@]}" -gt 0 ]; then
    printf 'FAILED: %s\n' "${FAILED[@]}"
    exit 1
fi
exit 0
