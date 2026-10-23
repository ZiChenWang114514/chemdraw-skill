"""How closely a rendered drawing follows the source image.

Both images are cropped to their ink, the candidate is scaled uniformly onto
the reference box and shifted a few pixels to the best match.  Ink IoU is
measured after dilating both by a small tolerance, so stroke width and
anti-aliasing do not dominate the score.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _ink(path):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f'Cannot read image {path}')
    if img.ndim == 3 and img.shape[2] == 4:  # transparent render background -> white
        alpha = img[:, :, 3:4].astype(float) / 255
        img = (img[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ink = gray < 160
    ys, xs = np.nonzero(ink)
    if not len(xs):
        raise ValueError(f'No ink in {path}')
    return ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def compare(reference, candidate, overlay_path=None, tolerance: int = 3, search: int = 12) -> dict:
    ref = _ink(reference)
    cand = _ink(candidate)
    h, w = ref.shape
    k = (w / cand.shape[1] + h / cand.shape[0]) / 2
    cand = cv2.resize(cand.astype(np.uint8) * 255, (max(1, round(cand.shape[1] * k)), max(1, round(cand.shape[0] * k))),
                      interpolation=cv2.INTER_AREA) > 60
    pad = search + tolerance + 2
    canvas_h, canvas_w = max(h, cand.shape[0]) + 2 * pad, max(w, cand.shape[1]) + 2 * pad
    R = np.zeros((canvas_h, canvas_w), bool)
    R[pad:pad + h, pad:pad + w] = ref
    kernel = np.ones((2 * tolerance + 1, 2 * tolerance + 1), np.uint8)
    Rd = cv2.dilate(R.astype(np.uint8), kernel) > 0
    best = (-1.0, 0, 0)
    for dy in range(-search, search + 1, 2):
        for dx in range(-search, search + 1, 2):
            C = np.zeros_like(R)
            y0, x0 = pad + dy, pad + dx
            C[y0:y0 + cand.shape[0], x0:x0 + cand.shape[1]] = cand
            Cd = cv2.dilate(C.astype(np.uint8), kernel) > 0
            # an ink pixel matches when the other image has ink within the tolerance
            hit = (R & Cd).sum() + (C & Rd).sum()
            score = hit / max(1, R.sum() + C.sum())
            if score > best[0]:
                best = (score, dx, dy)
    score, dx, dy = best
    C = np.zeros_like(R)
    C[pad + dy:pad + dy + cand.shape[0], pad + dx:pad + dx + cand.shape[1]] = cand
    Cd = cv2.dilate(C.astype(np.uint8), kernel) > 0
    result = {'match': round(float(score), 4),
              'reference_unmatched': round(float((R & ~Cd).sum() / max(1, R.sum())), 4),
              'candidate_unmatched': round(float((C & ~Rd).sum() / max(1, C.sum())), 4),
              'scale': round(float(k), 4), 'shift': [dx, dy]}
    if overlay_path:
        out = np.full((canvas_h, canvas_w, 3), 255, np.uint8)
        out[R] = (60, 60, 230)          # reference only: red
        out[C] = (230, 120, 30)         # candidate only: blue
        out[R & C] = (40, 40, 40)
        cv2.imwrite(str(Path(overlay_path)), out)
        result['overlay'] = str(overlay_path)
    return result
