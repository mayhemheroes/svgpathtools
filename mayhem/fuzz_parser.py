#! /usr/bin/env python3
# NOTE: this file MUST stay executable (mode 0755). Mayhem runs libFuzzer in FORK mode and re-launches
# the harness for every job via sys.argv[0] — which, because the ELF launcher exec's `python3
# fuzz_parser.py`, is THIS script's path. A non-executable harness makes that re-exec fail with EACCES,
# every fork child dies before running an input, and Mayhem records 0 edges. chmod +x.
"""Atheris fuzz harness for svgpathtools' SVG path / document parsers.

Exercises the three public parse entry points:
  - svgpathtools.parse_path  (the SVG path "d" mini-language grammar)
  - svgpathtools.svg2paths   (parse a whole SVG document -> paths)
  - svgpathtools.svg2paths2  (same, also returning svg attributes)

Malformed input is *expected* to raise a handful of parse/validation errors; those are swallowed
(return -1) so only an unexpected, uncaught exception (a real defect in the fuzzed code) is reported.

Atheris is a libFuzzer engine: run with libFuzzer flags it iterates; run with a single file argument
it replays that input once (standalone reproducer). The ELF launcher (launcher.c) exec's python3 on
this file, forwarding every argument unchanged.

COVERAGE NOTE: instrumentation is scoped with include=['svgpathtools', 'xml'] — it instruments the
svgpathtools package (the path / "d" mini-language grammar parser, the real target) AND xml.dom.minidom
(the document backend svg2paths* drive), but NOT numpy/scipy. A BARE instrument_imports() (no include=)
also instruments svgpathtools' heavy numeric deps numpy+scipy (~580 modules), which makes Atheris spend
~32s patching bytecode at startup. Mayhem runs libFuzzer in fork mode, re-launching the harness for
every job, so that 32s startup is paid per child: workers never finish initializing, coverage stays
pinned at its INITED value, and Mayhem records ~0 edges. Scoping to the parser + xml backend cuts
startup to ~2s and lets the fork workers actually fuzz. The ExpatError import is kept INSIDE the block
so the xml backend is reached only under instrumentation, never cached uninstrumented.
"""
import sys
from io import BytesIO
from contextlib import contextmanager

import atheris
import fuzz_helpers

with atheris.instrument_imports(include=['svgpathtools', 'xml']):
    # Errors raised on malformed XML (svg2paths*) — imported INSIDE the block so the backend
    # (xml.dom.minidom / pyexpat) is reached only under instrumentation, never cached uninstrumented.
    from pyexpat import ExpatError
    import svgpathtools


# Disable stdout/stderr so noisy parse paths don't slow the fuzzer.
@contextmanager
def nostdout():
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    sys.stdout = BytesIO()
    sys.stderr = BytesIO()
    yield
    sys.stdout = save_stdout
    sys.stderr = save_stderr


def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            svgpathtools.parse_path(fdp.ConsumeRemainingString())
        elif choice == 1:
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=False) as f, nostdout():
                svgpathtools.svg2paths(f)
        else:
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=False) as f, nostdout():
                svgpathtools.svg2paths2(f)
    except ExpatError:
        return -1
    # The remaining handlers swallow the parse/validation errors that malformed input legitimately
    # provokes inside the grammar / document parsers; without them an uncaught exception aborts the
    # whole fuzzing run after a few thousand iterations, freezing coverage near zero.
    except AttributeError as e:
        # 'read' -> duck-typed file object on garbage; "'NoneType' ... 'real'" -> a path command
        # consumed before any current position was established (malformed "d" mini-language).
        if 'read' in str(e) or "'real'" in str(e) or "'imag'" in str(e):
            return -1
        raise
    except ValueError as e:
        # 'Unallowed' -> rejected path command; the rest are float()/coordinate conversion failures
        # and numpy/document validation errors on malformed coordinate data.
        return -1
    except IndexError as e:
        if 'pop from empty list' in str(e) or 'index out of range' in str(e):
            return -1
        raise
    except TypeError as e:
        # '<string>'/'bytes-like' -> non-text fed to a text parser; "...'NoneType'..." -> a relative
        # path command applied before any current position was set (malformed "d" mini-language).
        if '<string>' in str(e) or 'bytes-like' in str(e) or 'NoneType' in str(e):
            return -1
        raise
    except AssertionError:
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
