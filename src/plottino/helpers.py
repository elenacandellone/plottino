"""Small helpers for common figure chores: panel letters, emphasis, direct labels."""
import string

import numpy as np

from .colors import GREY
from .style import current_journal


def panel_labels(axes, labels=None, x=-0.12, y=1.04, case=None, fontsize=None, **kwargs):
    """Put bold panel letters (A, B, ... or a, b, ...) at the top-left of each axes.

    case: 'upper' or 'lower' (default: the journal's convention). x, y are in axes fractions.
    """
    j = current_journal()
    axes = list(np.ravel(axes))
    if labels is None:
        letters = string.ascii_uppercase if (case or j.panel_label_case) == 'upper' else string.ascii_lowercase
        labels = letters[:len(axes)]
    style = dict(fontsize=fontsize or j.font_size + 1, fontweight='bold', va='bottom', ha='left')
    style.update(kwargs)
    return [ax.text(x, y, lab, transform=ax.transAxes, **style) for ax, lab in zip(axes, labels)]


def emphasize(ax, keep, color=GREY):
    """Grey out every line/collection/patch in ax except those whose label is in `keep`,
    so the message is carried by the few that stay coloured."""
    keep = {keep} if isinstance(keep, str) else set(keep)
    for a in (*ax.lines, *ax.collections, *ax.patches):
        if a.get_label() in keep:
            a.set_zorder(a.get_zorder() + 1)
            continue
        if hasattr(a, 'set_color'):
            a.set_color(color)
        elif hasattr(a, 'set_facecolor'):
            a.set_facecolor(color)


def label_lines(ax, lines=None, dx=4, fontsize=None, **kwargs):
    """Label each line at its right end with its label, in the text colour (replaces a legend).

    Labels are nudged apart vertically when they would collide.
    """
    lines = [l for l in (lines or ax.lines) if not l.get_label().startswith('_')]
    if not lines:
        return []
    fig = ax.figure
    fig.canvas.draw()
    pts = []
    for l in lines:
        x, y = np.asarray(l.get_xdata(), float), np.asarray(l.get_ydata(), float)
        ok = np.isfinite(x) & np.isfinite(y)
        i = np.flatnonzero(ok)[np.argmax(x[ok])]
        pts.append(ax.transData.transform((x[i], y[i])))
    size = fontsize or current_journal().font_size
    gap = size * 1.2 * fig.dpi / 72
    order = np.argsort([p[1] for p in pts])
    ys = [pts[i][1] for i in order]
    for k in range(1, len(ys)):          # push labels up until they no longer touch
        ys[k] = max(ys[k], ys[k - 1] + gap)
    shift = (np.mean([pts[i][1] for i in order]) - np.mean(ys))
    # keep the labels inside the axes, clear of the axis lines
    lo, hi = ax.bbox.y0 + gap / 2, ax.bbox.y1 - gap / 2
    shift = max(shift, lo - ys[0])
    shift = min(shift, hi - ys[-1]) if ys[-1] + shift > hi and ys[0] + (hi - ys[-1]) >= lo else shift
    ys = [y + shift for y in ys]
    inv = ax.transData.inverted()
    texts = []
    for k, i in enumerate(order):
        x_disp = pts[i][0] + dx * fig.dpi / 72
        xd, yd = inv.transform((x_disp, ys[k]))
        texts.append(ax.text(xd, yd, lines[i].get_label(), va='center', ha='left', fontsize=size,
                             clip_on=False, **kwargs))
    return texts
