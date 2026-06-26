#!/usr/bin/env python3
"""Oracle driver for mayhem/test.sh — read an SVG path "d" string from a file and print a fixed set
of ``KEY=value`` lines describing the parsed Path (a known-answer dump).

This exercises the SAME parse path the fuzzer drives (svgpathtools.parse_path -> Path of segments),
and prints decoded structural values, so a neutered/no-op program produces no/garbled output and the
test.sh assertions fail. Invoked via the /mayhem/run-cli ELF launcher (a non-system executable, so
the verify-repo sabotage neuter applies to it).
"""
import sys

import svgpathtools


def main():
    with open(sys.argv[1], "r") as fh:
        d = fh.read().strip()

    path = svgpathtools.parse_path(d)

    print(f"NumSegments={len(path)}")
    for i, seg in enumerate(path):
        print(f"Segment{i}={type(seg).__name__}")
    # Complex points printed as "<real>,<imag>" to keep the known-answer stable.
    start = path.start
    end = path.end
    print(f"Start={start.real:g},{start.imag:g}")
    print(f"End={end.real:g},{end.imag:g}")
    # Round-trip: re-serialising the parsed path must yield a non-empty "d" string.
    print(f"Reserialized={'yes' if path.d() else 'no'}")
    print(f"Closed={path.isclosed()}")


if __name__ == "__main__":
    main()
