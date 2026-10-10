import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools', 'pixelart'))
from line_check import line_violations, line_mask


def _mask(rows):
    return np.array([[c == '#' for c in row] for row in rows])


def test_clean_diagonal_and_straight_lines_pass():
    m = _mask([
        '#.....',
        '.#....',
        '..####',
        '......',
    ])
    assert line_violations(m)['total'] == 0


def test_2x2_block_fails():
    m = _mask(['....', '.##.', '.##.', '....'])
    assert line_violations(m)['blocks'] == 1


def test_l_corner_fails():
    # the middle pixel of an L (one horizontal and one vertical neighbour, no diagonal) is a doubled step
    m = _mask(['#...', '##..', '....', '....'])
    assert line_violations(m)['l_corners'] > 0


def test_isolated_and_short_pieces_fail():
    m = _mask(['#.....', '......', '...##.', '......'])
    v = line_violations(m)
    assert v['isolated'] == 1
    assert v['short'] == 3  # the isolated pixel and the 2 px piece


def test_line_mask_is_the_pixel_difference():
    a = np.zeros((2, 2, 3), dtype=np.uint8)
    b = a.copy()
    b[0, 1] = 255
    assert line_mask(b, a).tolist() == [[False, True], [False, False]]


def test_marker_mask_is_magenta_and_cyan_only():
    from line_check import marker_mask
    a = np.zeros((1, 4, 3), dtype=np.uint8)
    a[0, 0] = (255, 0, 255)
    a[0, 1] = (0, 255, 255)
    a[0, 2] = (255, 0, 254)
    assert marker_mask(a).tolist() == [[True, True, False, False]]
