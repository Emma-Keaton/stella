import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure tests can import the application package from the workspace root.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sandbox():
    """A scratch directory that is always cleaned up.

    Deliberately does NOT use pytest's `tmp_path`: in some sandboxes pytest
    cannot create its `pytest-of-<user>` base directory, which fails every
    test in a module at setup time with PermissionError. tempfile.mkdtemp()
    sidesteps that entirely.
    """
    d = Path(tempfile.mkdtemp(prefix="stella-test-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)

