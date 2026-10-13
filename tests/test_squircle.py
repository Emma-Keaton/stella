"""Tests for the shared squircle shape (core/shapes.py).

The squircle is used by the desktop splash, the chat avatar and the mobile
app icon, so it is worth pinning its behaviour: a squircle is a *rounded
square*, not a circle, and the same maths must drive every surface.
"""

from __future__ import annotations

import math

import pytest

from core import shapes


def test_points_lie_on_the_superellipse():
    pts = shapes.superellipse_points(50, 50, 40, 40, n=4.0)
    for x, y in pts:
        value = abs((x - 50) / 40) ** 4.0 + abs((y - 50) / 40) ** 4.0
        assert math.isclose(value, 1.0, abs_tol=1e-6)


def test_squircle_is_not_a_circle():
    # A circle of radius 50 centred in a 100 box reaches (100, 50) at the
    # right edge-midpoint. A squircle reaches further out toward the corners,
    # and its corners of the *bounding box* stay outside.
    assert shapes.is_inside(50, 50, 100, n=4.0)
    assert shapes.is_inside(50, 1, 100, n=4.0)      # edge midpoint: on the shape
    assert not shapes.is_inside(1, 1, 100, n=4.0)   # box corner: outside


def test_n_two_approximates_a_circle():
    # With n=2 the shape must be an ellipse: the box corner is outside and the
    # diagonal at 45 degrees sits on the curve.
    r = 40
    cx = cy = 50
    diag = r / math.sqrt(2)
    assert shapes.is_inside(cx + diag, cy + diag, 100, n=2.0)
    assert not shapes.is_inside(2, 2, 100, n=2.0)


def test_svg_path_is_closed_and_non_empty():
    d = shapes.svg_path(96)
    assert d.startswith("M ")
    assert d.rstrip().endswith("Z")
    assert d.count("L ") >= 100


def test_bad_exponent_rejected():
    with pytest.raises(ValueError):
        shapes.superellipse_points(0, 0, 1, 1, n=0)


@pytest.mark.skipif(
    pytest.importorskip("PyQt6", reason="PyQt6 not installed") is None,
    reason="PyQt6 not installed",
)
def test_qt_badge_masks_corners():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap

    app = QApplication.instance() or QApplication([])
    badge = shapes.qt_badge(QPixmap(48, 48), 48, background="#0B0F18", inset=0.2)
    image = badge.toImage()
    assert image.pixelColor(0, 0).alpha() == 0        # corner masked away
    assert image.pixelColor(24, 24).alpha() > 0       # body painted
    del app


def test_qcolor_parses_css():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    assert shapes._qcolor("rgba(12,14,20,245)").getRgb()[:3] == (12, 14, 20)
    assert shapes._qcolor("rgba(124,110,230,0.5)").getRgb() == (124, 110, 230, 128)
    del app
