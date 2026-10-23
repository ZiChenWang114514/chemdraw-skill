"""Synthetic Markush line drawings with known geometry, for detection tests."""
from __future__ import annotations

import math

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX


def _text(img, s, center, scale=1.1, thick=2):
    (w, h), _ = cv2.getTextSize(s, FONT, scale, thick)
    cv2.putText(img, s, (int(center[0] - w / 2), int(center[1] + h / 2)), FONT, scale, 0, thick, cv2.LINE_AA)
    return w, h


def benzene_with_groups(path):
    """Benzene ring (alternating double bonds), an R label on one atom, a variable
    ring circle "A" bonded to another atom, and an (X)n group whose line starts
    inside the benzene ring.  Returns the known geometry."""
    img = np.full((520, 760), 255, np.uint8)
    c, r = np.array([300.0, 260.0]), 70.0
    pts = [c + r * np.array([math.cos(math.radians(90 + 60 * k)), -math.sin(math.radians(90 + 60 * k))])
           for k in range(6)]
    for k in range(6):
        a, b = pts[k], pts[(k + 1) % 6]
        cv2.line(img, tuple(map(int, a)), tuple(map(int, b)), 0, 3, cv2.LINE_AA)
        if k % 2 == 0:  # inner line of a double bond
            ia, ib = a + (c - a) * 0.18, b + (c - b) * 0.18
            ia, ib = ia + (ib - ia) * 0.12, ib + (ia - ib) * 0.12
            cv2.line(img, tuple(map(int, ia)), tuple(map(int, ib)), 0, 3, cv2.LINE_AA)
    top = pts[0]
    r_pos = top + np.array([0, -75])
    cv2.line(img, tuple(map(int, top)), tuple(map(int, r_pos + np.array([0, 22]))), 0, 3, cv2.LINE_AA)
    _text(img, 'R', r_pos)
    # variable ring A to the right of atom 5 (lower right)
    right = pts[5]
    ring_c = right + np.array([150, 0])
    cv2.circle(img, tuple(map(int, ring_c)), 55, 0, 3, cv2.LINE_AA)
    _text(img, 'A', ring_c)
    cv2.line(img, tuple(map(int, right)), tuple(map(int, ring_c - np.array([55, 0]))), 0, 3, cv2.LINE_AA)
    # (X)n group from inside the ring, through the lower-left bond, to its label
    start = c + np.array([-25, 25])
    label = c + np.array([-140, 150])
    end = label + np.array([30, -30])
    cv2.line(img, tuple(map(int, start)), tuple(map(int, end)), 0, 3, cv2.LINE_AA)
    _text(img, '(X)n', label)
    cv2.imwrite(str(path), img)
    return {'ring': pts, 'circle': (ring_c, 55), 'r_label': r_pos, 'group_label': label}
