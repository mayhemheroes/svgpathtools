#! /usr/bin/env python3

import atheris
import sys
import fuzz_helpers
from io import BytesIO
from contextlib import contextmanager

# Errors
from pyexpat import ExpatError

with atheris.instrument_imports(include=["svgpathtools"]):
    import svgpathtools

# Disable stdout
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
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=False), nostdout() as f:
                svgpathtools.svg2paths(f)
        else:
            with fdp.ConsumeMemoryFile(all_data=True, as_bytes=False), nostdout() as f:
                svgpathtools.svg2paths2(f)
    except ExpatError:
        return -1
    # These are raised too often to allow
    except AttributeError as e:
        if 'read' in str(e):
            return -1
        raise
    except ValueError as e:
        if 'Unallowed' in str(e):
            return -1
    except IndexError as e:
        if 'pop from empty list' in str(e):
            return -1
        raise
    except TypeError as e:
        if '<string>' in str(e) or 'bytes-like' in str(e):
            return -1
        raise
    except AssertionError as e:
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
