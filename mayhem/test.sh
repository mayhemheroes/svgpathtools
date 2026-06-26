#!/usr/bin/env bash
#
# svgpathtools/mayhem/test.sh — behavioral oracle for mathandy/svgpathtools.
#
# It RUNS the real parser (via the /mayhem/run-cli launcher built by mayhem/build.sh) over a known
# SVG path "d" string fixture and ASSERTS the parsed structure (known-answer test): segment count,
# segment types, start/end points, round-trip serialisation. This exercises the SAME pipeline the
# fuzzer drives — read string -> parse_path -> Path of segments — so a no-op/neutered program (no
# output, or wrong output) FAILS here. It never builds; it only runs the pre-built launcher.
#
# Anti-reward-hack note: run-cli lives at /mayhem (a NON-system path), so the verify-repo sabotage
# neuter (_exit(0) on non-system exes) trips it -> empty output -> assertions fail -> detected.
set -uo pipefail
[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH
: "${SRC:=/mayhem}"
cd "$SRC"

CLI="$SRC/run-cli"
FIXTURE="$SRC/mayhem/testsuite/seed"

# emit_ctrf <tool> <passed> <failed> [skipped] [pending] [other]
emit_ctrf() {
  local tool="$1" passed="$2" failed="$3" skipped="${4:-0}" pending="${5:-0}" other="${6:-0}"
  local tests=$(( passed + failed + skipped + pending + other ))
  cat > "${CTRF_REPORT:-$SRC/ctrf-report.json}" <<JSON
{
  "results": {
    "tool": { "name": "$tool" },
    "summary": {
      "tests": $tests,
      "passed": $passed,
      "failed": $failed,
      "pending": $pending,
      "skipped": $skipped,
      "other": $other
    }
  }
}
JSON
  printf 'CTRF {"results":{"tool":{"name":"%s"},"summary":{"tests":%d,"passed":%d,"failed":%d,"pending":%d,"skipped":%d,"other":%d}}}\n' \
    "$tool" "$tests" "$passed" "$failed" "$pending" "$skipped" "$other"
  [ "$failed" -eq 0 ]
}

PASS=0; FAIL=0
check() { # check <name> <condition-rc>
  if [ "$2" -eq 0 ]; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1"; FAIL=$((FAIL+1)); fi
}

if [ ! -x "$CLI" ]; then
  echo "missing $CLI — run mayhem/build.sh first" >&2
  emit_ctrf "svgpathtools-knownanswer" 0 1 0; exit 2
fi
if [ ! -f "$FIXTURE" ]; then
  echo "missing $FIXTURE" >&2
  emit_ctrf "svgpathtools-knownanswer" 0 1 0; exit 2
fi

echo "=== parsing fixture '$(cat "$FIXTURE")' (structure dump to stdout) ==="
OUT="$("$CLI" "$FIXTURE" 2>/dev/null)"
echo "$OUT"

# Known answers for the bundled seed fixture:
#   "M 300 100 C 100 100 200 200 200 300 L 250 350"
#   => CubicBezier (300,100)->(200,300), then Line (200,300)->(250,350)
grep -q '^NumSegments=2$'        <<<"$OUT"; check "segment count" $?
grep -q '^Segment0=CubicBezier$' <<<"$OUT"; check "first segment is CubicBezier" $?
grep -q '^Segment1=Line$'        <<<"$OUT"; check "second segment is Line" $?
grep -q '^Start=300,100$'        <<<"$OUT"; check "path start point" $?
grep -q '^End=250,350$'          <<<"$OUT"; check "path end point" $?
grep -q '^Reserialized=yes$'     <<<"$OUT"; check "path round-trips to a d() string" $?
grep -q '^Closed=False$'         <<<"$OUT"; check "open path reported not-closed" $?

emit_ctrf "svgpathtools-knownanswer" "$PASS" "$FAIL" 0
