"""Colour tools: a colour-blind-safe palette, OKLab distances, colour-vision-deficiency
simulation and text contrast.

CVD simulation uses the Machado, Oliveira & Fernandes (2009) matrices at full severity,
applied in linear sRGB. Distances are Euclidean OKLab (Ottosson 2020) x 100, so a
difference of ~2 is just noticeable and ~10 is easy to see.
"""
import numpy as np
from matplotlib.colors import to_rgba

# Okabe & Ito (2008), "Color Universal Design": distinguishable under the common CVD types.
OKABE_ITO = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9', '#D55E00', '#F0E442', '#000000']
TEXT = '#404040'   # dark grey text: softer than black, still high contrast on white
GREY = '#a8a8a8'   # context / de-emphasised data
LIGHT = '#d9d9d9'  # grid lines and reference marks

_CVD = {
    'protanopia': np.array([[0.152286, 1.052583, -0.204868],
                            [0.114503, 0.786281, 0.099216],
                            [-0.003882, -0.048116, 1.051998]]),
    'deuteranopia': np.array([[0.367322, 0.860646, -0.227968],
                              [0.280085, 0.672501, 0.047413],
                              [-0.011820, 0.042940, 0.968881]]),
    'tritanopia': np.array([[1.255528, -0.076749, -0.178779],
                            [-0.078411, 0.930809, 0.147602],
                            [0.004733, 0.691367, 0.303900]]),
}


def _rgb(c):
    return np.array(to_rgba(c)[:3], dtype=float)


def _to_linear(rgb):
    rgb = np.asarray(rgb, dtype=float)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def oklab(c):
    """OKLab coordinates (L, a, b) of a matplotlib colour."""
    return _oklab_linear(_to_linear(_rgb(c)))


def _oklab_linear(lin):
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return m2 @ np.cbrt(m1 @ np.clip(lin, 0, 1))


def simulate(c, kind):
    """OKLab coordinates of colour c as seen with a colour-vision deficiency
    ('protanopia', 'deuteranopia' or 'tritanopia')."""
    return _oklab_linear(_CVD[kind] @ _to_linear(_rgb(c)))


def distance(c1, c2, kind=None):
    """OKLab distance x 100 between two colours, for normal vision (kind=None) or a CVD type."""
    if kind is None:
        return 100 * float(np.linalg.norm(oklab(c1) - oklab(c2)))
    return 100 * float(np.linalg.norm(simulate(c1, kind) - simulate(c2, kind)))


def worst_cvd(c1, c2):
    """(smallest distance x 100 over the CVD types, the type giving it)."""
    return min((distance(c1, c2, k), k) for k in _CVD)


def luminance(c):
    """WCAG relative luminance."""
    return float(_to_linear(_rgb(c)) @ np.array([0.2126, 0.7152, 0.0722]))


def contrast(c1, c2):
    """WCAG contrast ratio (1-21); 4.5 is the usual floor for small text, 3 for large."""
    l1, l2 = sorted((luminance(c1), luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def chroma(c):
    _, a, b = oklab(c)
    return float(np.hypot(a, b))


def check_palette(colors, normal_min=10.0, cvd_min=8.0):
    """Pairs of colours that are hard to tell apart.

    Returns a list of (c1, c2, what, distance) where `what` is 'normal' or a CVD type;
    a pair is reported if its normal-vision distance is below normal_min or its
    worst CVD distance is below cvd_min.
    """
    colors = list(dict.fromkeys(colors))
    out = []
    for i, c1 in enumerate(colors):
        for c2 in colors[i + 1:]:
            d = distance(c1, c2)
            if d < normal_min:
                out.append((c1, c2, 'normal', d))
                continue
            dc, kind = worst_cvd(c1, c2)
            if dc < cvd_min:
                out.append((c1, c2, kind, dc))
    return out
