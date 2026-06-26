#!/usr/bin/env bash
#
# svgpathtools/mayhem/build.sh — build the Atheris fuzz target for mathandy/svgpathtools.
#
# This is a PYTHON (Atheris/libFuzzer) project, so the "build" is:
#   1) install svgpathtools + its deps + atheris, OFFLINE, from the wheelhouse the Dockerfile baked
#      into /opt/toolchains/python/wheelhouse (air-gapped, re-runnable — SPEC §6.5);
#   2) compile tiny ELF launchers (launcher.c) so the Mayhem target `cmd` is a native executable
#      (Mayhem rejects script targets; fuzz-smoke checks the ELF magic). Each launcher exec's
#      `python3 <script> "$@"`, forwarding libFuzzer flags to Atheris:
#        - /mayhem/fuzz_parser             : the Mayhem libFuzzer target (Atheris iterates).
#        - /mayhem/fuzz_parser-standalone  : run-once reproducer (Atheris replays one file arg).
#        - /mayhem/run-cli                 : the oracle runner mayhem/test.sh drives (show_path.py).
#
# NOTE on sanitizers: the fuzzed code is Python; coverage/instrumentation come from Atheris
# (atheris.instrument_imports), not from clang $SANITIZER_FLAGS — those apply to native C/C++ code,
# of which this project has none. We still thread $DEBUG_FLAGS into the launcher compile so the
# spec's debug-info contract (DWARF < 4) holds on every emitted ELF.
set -euo pipefail

# clang rejects SOURCE_DATE_EPOCH='' — must be unset or a valid integer.
[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH

# `=` (not `:=`) so an explicit empty --build-arg SANITIZER_FLAGS= builds without sanitizers.
: "${SANITIZER_FLAGS=-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer}"
# DEBUG_FLAGS: explicit DWARF-3 so Mayhem triage can read symbols (clang-19's plain -g emits DWARF-5).
: "${DEBUG_FLAGS:=-g -gdwarf-3}"
: "${CC:=clang}"
: "${SRC:=/mayhem}"
: "${WHEELHOUSE:=/opt/toolchains/python/wheelhouse}"
export SANITIZER_FLAGS DEBUG_FLAGS CC SRC WHEELHOUSE
OUT=/mayhem

cd "$SRC"

# ── 1) Python deps — OFFLINE from the baked wheelhouse (idempotent; "already satisfied" on re-run) ──
PIP="python3 -m pip install --user --break-system-packages"
if [ -d "$WHEELHOUSE" ] && [ -n "$(ls -A "$WHEELHOUSE" 2>/dev/null)" ]; then
  $PIP --no-index --find-links "$WHEELHOUSE" atheris setuptools wheel numpy scipy svgwrite
  $PIP --no-index --find-links "$WHEELHOUSE" --no-build-isolation .
else
  # First build only (no wheelhouse yet): allow the network. The Dockerfile bakes the wheelhouse so
  # the air-gapped PATCH re-run takes the --no-index branch above.
  $PIP atheris setuptools wheel numpy scipy svgwrite
  $PIP --no-build-isolation .
fi

# Sanity: the harnessed module must import.
python3 -c 'import atheris, svgpathtools; svgpathtools.parse_path' \
  || { echo "FATAL: svgpathtools failed to import" >&2; exit 1; }

# ── 2) Native ELF launchers ─────────────────────────────────────────────────────────────────────
# Sanitizing a ~30-line exec shim is pointless (and would drag the ASan runtime into the python
# child), so the launcher is built WITHOUT $SANITIZER_FLAGS but WITH $DEBUG_FLAGS (DWARF-3) to
# satisfy the debug-info contract. The Python code itself is instrumented by Atheris.
"$CC" $DEBUG_FLAGS -O1 \
    -DHARNESS_PATH="\"$SRC/mayhem/fuzz_parser.py\"" \
    -o "$OUT/fuzz_parser" "$SRC/mayhem/launcher.c"

# Standalone run-once reproducer: same binary (Atheris replays a single file argument).
cp -f "$OUT/fuzz_parser" "$OUT/fuzz_parser-standalone"

# CLI runner for the test oracle: exec's show_path.py. Because it lives at a NON-system path, the
# anti-reward-hack neuter (LD_PRELOAD _exit(0) on non-system exes) trips it, making mayhem/test.sh
# a genuinely behavioral oracle.
"$CC" $DEBUG_FLAGS -O1 \
    -DHARNESS_PATH="\"$SRC/mayhem/show_path.py\"" \
    -o "$OUT/run-cli" "$SRC/mayhem/launcher.c"

echo "build.sh complete:"
ls -la "$OUT/fuzz_parser" "$OUT/fuzz_parser-standalone" "$OUT/run-cli"
