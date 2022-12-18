#! /usr/bin/env python3

import atheris
import sys
import fuzz_helpers

# Errrors
from pyexpat import ExpatError

with atheris.instrument_imports(include=["svgpathtools"]):
    import svgpathtools

def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    try:
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            path = svgpathtools.parse_path(fdp.ConsumeRemainingString())
        elif choice == 1:
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=True) as f:
                svgpathtools.svg2paths(f)
        else:
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=True) as f:
                svgpathtools.svg2paths2(f)


    except (IndexError, ValueError, TypeError, AttributeError, ExpatError):
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
