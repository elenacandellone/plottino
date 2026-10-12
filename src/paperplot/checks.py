"""check(fig): render a figure and report what would make it hard to read in print.

Every check works on what matplotlib actually draws (text and artist extents from a real
render), at the size the figure will be printed. Checks:

    size            figure width matches a column width of the journal; height fits the page
    text_overlap    two pieces of text overlap (tick labels, labels, annotations, legends)
    text_clipped    text is cut off at the figure edge or by axes clipping
    text_over_data  annotation or legend text sits on lines, markers or low-contrast fills
    legend_over_data  a legend box covers data
    font_size       text smaller than the journal minimum (or larger than its maximum)
    font_family     text not set in one of the journal's fonts
    line_width      lines thinner than the journal minimum
    contrast        text colour too close to its background
    colors          data colours hard to tell apart, with normal vision or colour blindness
    colormap        rainbow colormaps (jet, hsv, ...)
    labels          axes without labels, labels that look like variable names, several
                    labelled series without a legend
"""
import re
from dataclasses import dataclass, field

import numpy as np
import matplotlib as mpl
from matplotlib.collections import LineCollection, PathCollection, PolyCollection
from matplotlib.colors import to_hex, to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from . import colors as pcolors
from . import journals
from .style import current_journal

SEVERITIES = ('error', 'warning', 'info')
ALL_CHECKS = ('size', 'text_overlap', 'text_clipped', 'text_over_data', 'legend_over_data',
              'font_size', 'font_family', 'line_width', 'contrast', 'colors', 'colormap', 'labels')
RAINBOW_CMAPS = {'jet', 'rainbow', 'hsv', 'gist_rainbow', 'nipy_spectral', 'gist_ncar', 'prism',
                 'flag', 'spectral', 'gist_stern'}
HIGHLIGHT_GID = 'paperplot-highlight'


@dataclass
class Issue:
    check: str
    severity: str
    message: str
    bboxes: list = field(default_factory=list, repr=False)  # display coordinates, for highlight()

    def __str__(self):
        mark = {'error': 'x', 'warning': '!', 'info': 'i'}[self.severity]
        return f'  {mark} {self.severity:<7} {self.check:<16} {self.message}'


class FigureCheckError(Exception):
    pass


class Report:
    """The issues found in a figure. Print it, test `report.ok`, or draw boxes with highlight()."""

    def __init__(self, fig, journal, target_width, issues, saved_size=None):
        self.fig, self.journal, self.target_width = fig, journal, target_width
        self.saved_size = saved_size if saved_size is not None else tuple(fig.get_size_inches())
        self.issues = sorted(issues, key=lambda i: SEVERITIES.index(i.severity))

    errors = property(lambda self: [i for i in self.issues if i.severity == 'error'])
    warnings = property(lambda self: [i for i in self.issues if i.severity == 'warning'])

    @property
    def ok(self):
        """True when there are no errors (warnings and infos allowed)."""
        return not self.errors

    def __len__(self):
        return len(self.issues)

    def __iter__(self):
        return iter(self.issues)

    def __str__(self):
        w, h = self.fig.get_size_inches()
        sw, sh = self.saved_size
        head = f'paperplot check: {self.journal.name}, figure {w:.2f} x {h:.2f} in'
        if abs(sw - w) > 0.01 or abs(sh - h) > 0.01:
            head += f', saved (tight) {sw:.2f} x {sh:.2f} in'
        if abs(self.target_width - sw) > 0.01:
            head += f', printed at {self.target_width:.2f} in wide'
        if not self.issues:
            return head + '\n  no issues found'
        counts = ', '.join(f'{n} {s}{"s" if n != 1 else ""}' for s in SEVERITIES
                           if (n := sum(i.severity == s for i in self.issues)))
        return '\n'.join([head, *map(str, self.issues), f'  {counts}'])

    __repr__ = __str__

    def raise_for_errors(self):
        if not self.ok:
            raise FigureCheckError(str(self))
        return self

    def highlight(self, severities=('error', 'warning'), color='red'):
        """Draw a numbered box around every problem area (remove them with clear_highlights)."""
        clear_highlights(self.fig)
        inv = self.fig.transFigure.inverted()
        boxes, numbers = {}, {}   # one box per area; issues on the same area share it
        n = 0
        for issue in self.issues:
            issue.message = re.sub(r'^\[\d+\] ', '', issue.message)
            if issue.severity not in severities or not issue.bboxes:
                continue
            n += 1
            issue.message = f'[{n}] {issue.message}'
            for k, bb in enumerate(issue.bboxes):
                key = tuple(np.round(bb.extents, 1))
                boxes.setdefault(key, bb.transformed(inv))
                if k == 0:
                    numbers.setdefault(key, []).append(str(n))
        for key, fb in boxes.items():
            self.fig.add_artist(Rectangle((fb.x0, fb.y0), fb.width, fb.height, transform=self.fig.transFigure,
                                          fill=False, edgecolor=color, linewidth=0.8, gid=HIGHLIGHT_GID,
                                          clip_on=False, zorder=1000))
            if key in numbers:
                self.fig.text(fb.x1, fb.y1, ','.join(numbers[key]), color=color, fontsize=6, fontweight='bold',
                              ha='left', va='bottom', gid=HIGHLIGHT_GID, zorder=1001)
        return self.fig


def clear_highlights(fig):
    for a in list(fig.findobj(lambda a: a.get_gid() == HIGHLIGHT_GID)):
        a.remove()


def ignore(artist, *checks):
    """Exempt an artist from some checks (all of them when none are named), e.g. a label
    that sits on a bar on purpose: pp.ignore(ax.text(...), 'text_over_data')."""
    artist._paperplot_ignore = set(checks) or set(ALL_CHECKS)
    return artist


def _ignored(artist, check):
    return check in getattr(artist, '_paperplot_ignore', ())


# ----------------------------------------------------------------------------------------
# rendering

@dataclass
class _DrawnText:
    text: Text
    bbox: Bbox          # axis-aligned extent, display px
    poly: np.ndarray    # the rotated box corners, display px
    desc: str
    kind: str           # 'tick', 'label', 'title', 'legend', 'annotation', 'figure'
    axes: object


def _render(fig):
    """Draw the figure and record every text actually drawn, with its extent."""
    drawn = []
    original = Text.draw

    def draw(self, renderer):
        original(self, renderer)
        if self.get_visible() and self.get_text().strip() and self.get_gid() != HIGHLIGHT_GID:
            drawn.append((self, renderer))

    Text.draw = draw
    try:
        fig.canvas.draw()
    finally:
        Text.draw = original
    renderer = fig.canvas.get_renderer()
    seen, out = set(), []
    for t, r in drawn:
        if id(t) in seen:
            continue
        seen.add(id(t))
        bb = _ink_bbox(t, t.get_window_extent(r))
        if bb.width <= 0 or bb.height <= 0:
            continue
        out.append((t, bb, _rotated_box(t, bb, r)))
    return renderer, out


def _ink_bbox(t, bb):
    """Drop blank leading/trailing lines from the extent of horizontal text: a title such as
    'Message\\n' (space left for a subtitle) only inks its first line."""
    lines = t.get_text().split('\n')
    if len(lines) < 2 or t.get_rotation() % 360 != 0:
        return bb
    lead = len(lines) - len('\n'.join(lines).lstrip('\n').split('\n'))
    trail = len(lines) - len('\n'.join(lines).rstrip('\n').split('\n'))
    if lead == trail == 0 or lead == len(lines):
        return bb
    h = bb.height / len(lines)
    return Bbox.from_extents(bb.x0, bb.y0 + trail * h, bb.x1, bb.y1 - lead * h)


def _rotated_box(t, bb, renderer):
    """Corners of the text's rotated box (its AABB is bb, and both share the centre)."""
    angle = t.get_rotation() % 180
    if angle in (0, 90):
        return np.array([[bb.x0, bb.y0], [bb.x1, bb.y0], [bb.x1, bb.y1], [bb.x0, bb.y1]])
    rot = t.get_rotation()
    try:
        t.set_rotation(0)
        w, h = t.get_window_extent(renderer).size
    finally:
        t.set_rotation(rot)
    th = np.deg2rad(rot)
    u, v = np.array([np.cos(th), np.sin(th)]) * w / 2, np.array([-np.sin(th), np.cos(th)]) * h / 2
    c = np.array([(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2])
    return np.array([c - u - v, c + u - v, c + u + v, c - u + v])


def _polys_overlap(p, q, tol):
    """Separating-axis test for two convex quadrilaterals; overlap must exceed tol px."""
    for poly in (p, q):
        for i in range(len(poly)):
            edge = poly[(i + 1) % len(poly)] - poly[i]
            axis = np.array([-edge[1], edge[0]])
            n = np.linalg.norm(axis)
            if n == 0:
                continue
            axis /= n
            a, b = p @ axis, q @ axis
            if min(a.max(), b.max()) - max(a.min(), b.min()) <= tol:
                return False
    return True


def _axes_name(fig, ax):
    axes = [a for a in fig.axes if a.get_visible()]
    i = axes.index(ax) if ax in axes else '?'
    title = ax.get_title() or ax.get_title('left') or ax.get_title('right')
    return f'axes {i}' + (f' "{_short(title)}"' if title else '')


def _short(s, n=28):
    s = ' '.join(str(s).split())
    return s if len(s) <= n else s[:n - 1] + '...'


def _describe(fig, texts):
    """Name each drawn text by its role ('x tick label "0.5" (axes 1)')."""
    roles = {}
    for ax in fig.axes:
        name = _axes_name(fig, ax)
        for axis, xy in ((ax.xaxis, 'x'), (ax.yaxis, 'y')):
            for t in axis.get_ticklabels(which='both'):
                roles[id(t)] = (f'{xy} tick label', 'tick', name)
            roles[id(axis.label)] = (f'{xy} label', 'label', name)
            roles[id(axis.get_offset_text())] = (f'{xy} offset text', 'tick', name)
        for t in (ax.title, getattr(ax, '_left_title', None), getattr(ax, '_right_title', None)):
            if t is not None:
                roles[id(t)] = ('title', 'title', name)
        for t in ax.texts:
            roles[id(t)] = ('annotation', 'annotation', name)
        leg = ax.get_legend()
        if leg is not None:
            for t in [*leg.get_texts(), leg.get_title()]:
                roles[id(t)] = ('legend text', 'legend', name)
    for leg in fig.legends:
        for t in [*leg.get_texts(), leg.get_title()]:
            roles[id(t)] = ('legend text', 'legend', 'figure')
    for t in fig.texts:
        roles[id(t)] = ('figure text', 'figure', 'figure')
    for attr, role in (('_suptitle', 'suptitle'), ('_supxlabel', 'figure x label'), ('_supylabel', 'figure y label')):
        if getattr(fig, attr, None) is not None:
            roles[id(getattr(fig, attr))] = (role, 'figure', 'figure')
    out = []
    for t, bb, poly in texts:
        role, kind, where = roles.get(id(t), ('text', 'annotation', 'figure'))
        ax = t.axes
        out.append(_DrawnText(t, bb, poly, f'{role} "{_short(t.get_text())}" ({where})', kind, ax))
    return out


# ----------------------------------------------------------------------------------------
# data geometry

def _data_artists(ax):
    arts = [a for a in (*ax.lines, *ax.collections, *ax.patches) if a.get_visible()]
    return [a for a in arts if a.get_gid() != HIGHLIGHT_GID]


def _clip(bb, artist):
    """The part of bb where the artist can be drawn (its clip box), or None."""
    if artist.get_clip_on() and artist.get_clip_box() is not None:
        return Bbox.intersection(bb, artist.get_clip_box())
    return bb


def _hits_data(bb, artist, dpi):
    """How text in bb meets the artist: 'line', 'marker', ('fill', facecolor) or None."""
    bb = _clip(bb, artist)
    if bb is None or bb.width <= 0 or bb.height <= 0:
        return None
    px = dpi / 72
    if isinstance(artist, Line2D):
        if artist.get_linestyle() not in ('None', '', ' ') and artist.get_linewidth() > 0:
            path = artist.get_transform().transform_path(artist.get_path())
            if path.intersects_bbox(bb, filled=False) or _any_inside(path.vertices, bb, 0):
                return 'line'
        if artist.get_marker() not in (None, 'None', '', ' ') and artist.get_markersize() > 0:
            pts = artist.get_transform().transform(artist.get_xydata())
            if _any_inside(pts, bb, artist.get_markersize() * px / 2):
                return 'marker'
        return None
    if isinstance(artist, PathCollection):
        offsets = artist.get_offsets()
        if len(offsets) == 0:
            return None
        pts = artist.get_offset_transform().transform(offsets)
        sizes = artist.get_sizes()
        r = (np.sqrt(sizes if len(sizes) else [36]) / 2 * px)
        r = np.broadcast_to(r if len(r) == len(pts) else r[0], len(pts))
        inside = ((pts[:, 0] + r > bb.x0) & (pts[:, 0] - r < bb.x1)
                  & (pts[:, 1] + r > bb.y0) & (pts[:, 1] - r < bb.y1))
        return 'marker' if inside.any() else None
    if isinstance(artist, LineCollection):
        tr = artist.get_transform()
        for p in artist.get_paths():
            if tr.transform_path(p).intersects_bbox(bb, filled=False):
                return 'line'
        return None
    if isinstance(artist, (PolyCollection, Patch)):
        if isinstance(artist, Patch):
            paths, tr = [artist.get_path()], artist.get_transform()
            faces = [artist.get_facecolor()]
            edge_visible = artist.get_linewidth() > 0 and to_rgba(artist.get_edgecolor())[3] > 0
        else:
            paths, tr = artist.get_paths(), artist.get_transform()
            faces = artist.get_facecolor()
            edge_visible = False
        for i, p in enumerate(paths):
            tp = tr.transform_path(p)
            face = faces[i % len(faces)] if len(faces) else (0, 0, 0, 0)
            if to_rgba(face)[3] > 0.05:
                if tp.intersects_bbox(bb, filled=True):
                    return ('fill', face)
            elif edge_visible and tp.intersects_bbox(bb, filled=False):
                return 'line'
    return None


def _any_inside(pts, bb, r):
    pts = np.asarray(pts, float)
    if pts.size == 0:
        return False
    pts = pts[np.isfinite(pts).all(axis=1)]
    return bool(((pts[:, 0] + r > bb.x0) & (pts[:, 0] - r < bb.x1)
                 & (pts[:, 1] + r > bb.y0) & (pts[:, 1] - r < bb.y1)).any())


def _shrink(bb, d):
    return Bbox.from_extents(bb.x0 + d, bb.y0 + d, max(bb.x0 + d, bb.x1 - d), max(bb.y0 + d, bb.y1 - d))


def _background(t, fig):
    """The colour behind a text: its own bbox patch, else the axes or figure face."""
    patch = t.get_bbox_patch()
    if patch is not None and to_rgba(patch.get_facecolor())[3] > 0.5:
        return patch.get_facecolor()
    if t.axes is not None and t.axes.patch.get_visible() and to_rgba(t.axes.patch.get_facecolor())[3] > 0.5:
        return t.axes.patch.get_facecolor()
    fc = fig.get_facecolor()
    return fc if to_rgba(fc)[3] > 0.5 else 'white'


def _has_solid_bbox(t):
    patch = t.get_bbox_patch()
    return patch is not None and to_rgba(patch.get_facecolor())[3] > 0.5


# ----------------------------------------------------------------------------------------
# the checks

def check(fig=None, journal=None, width=None, checks=None, skip=(), tolerance=0.5, tight=False,
          verbose=False):
    """Render `fig` and return a Report of readability problems at its printed size.

    journal: name or Journal (default: the figure's, else the one set by use()).
    width: the width the figure will be printed at, if not its own size: inches, a column
        name, or a fraction like r'0.5\\textwidth'. Font and line sizes are scaled to it.
    checks / skip: run only / leave out these checks (see paperplot.checks.ALL_CHECKS).
    tolerance: overlaps smaller than this (in points) are ignored.
    tight: the figure will be saved with bbox_inches='tight': the canvas is the tight box
        (text outside the figure is kept) and its size is what gets printed.
    verbose: also print the report.
    """
    import matplotlib.pyplot as plt
    fig = fig if fig is not None else plt.gcf()
    j = journals.get(journal) if journal is not None else getattr(fig, '_paperplot_journal', current_journal())
    run = set(checks or ALL_CHECKS) - set(skip)
    issues = []

    clear_highlights(fig)
    renderer, raw = _render(fig)
    texts = _describe(fig, raw)
    dpi = fig.dpi
    tol = tolerance * dpi / 72

    if tight:
        pad = mpl.rcParams['savefig.pad_inches']
        canvas = Bbox(fig.get_tightbbox(renderer).padded(pad).get_points() * dpi)
    else:
        canvas = fig.bbox
    target, scale = _size(fig, j, width, canvas.width / dpi, canvas.height / dpi,
                          issues if 'size' in run else [])
    ctx = dict(fig=fig, j=j, texts=texts, dpi=dpi, tol=tol, scale=scale, issues=issues, renderer=renderer,
               canvas=canvas, tight=tight)
    for name in ('text_overlap', 'text_clipped', 'text_over_data', 'legend_over_data', 'font_size',
                 'font_family', 'line_width', 'contrast', 'colors', 'colormap', 'labels'):
        if name in run:
            globals()[f'_check_{name}'](**ctx)
    report = Report(fig, j, target, issues, (canvas.width / dpi, canvas.height / dpi))
    if verbose:
        print(report)
    return report


def _size(fig, j, width, w, h, issues):
    spec = width if width is not None else getattr(fig, '_paperplot_width', None)
    if spec is not None:
        target = j.width(spec)
        if abs(target - w) / target > 0.02:
            issues.append(Issue('size', 'warning',
                                f'{"saved (tight) " if abs(w - fig.get_size_inches()[0]) > 0.01 else ""}'
                                f'width {w:.2f} in will be scaled to {target:.2f} in ({spec}), by '
                                f'{target / w:.0%}; fonts and lines are checked at that scale'))
    else:
        name, target = min(j.widths.items(), key=lambda kv: abs(kv[1] - w))
        if abs(target - w) / target > 0.02:
            issues.append(Issue('size', 'warning',
                                f'{"saved (tight) " if abs(w - fig.get_size_inches()[0]) > 0.01 else ""}'
                                f'width {w:.2f} in is not a {j.name} column width '
                                f'({", ".join(f"{k} {v:.2f}" for k, v in j.widths.items())} in); sizes are '
                                f'checked as if scaled to {name} ({target:.2f} in). Make the figure at its '
                                'printed size, or pass width='))
        else:
            target = w
    scale = target / w
    if h * scale > j.max_height * 1.001:
        issues.append(Issue('size', 'error',
                            f'printed height {h * scale:.2f} in exceeds the {j.name} maximum {j.max_height:.2f} in'))
    return target, scale


def _check_text_overlap(texts, tol, issues, **_):
    seen_tick_axes = set()
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if _ignored(a.text, 'text_overlap') or _ignored(b.text, 'text_overlap'):
                continue
            if not a.bbox.overlaps(b.bbox) or not _polys_overlap(a.poly, b.poly, tol):
                continue
            if a.kind == b.kind == 'tick' and a.desc.split('"')[0] == b.desc.split('"')[0]:
                key = (a.desc.split('"')[0], a.desc.rsplit('(', 1)[-1])
                if key in seen_tick_axes:
                    continue   # one message per crowded axis
                seen_tick_axes.add(key)
                issues.append(Issue('text_overlap', 'error',
                                    f'{a.desc.split(chr(34))[0].strip()}s overlap in {key[1].rstrip(")")}: '
                                    'use fewer ticks, rotate them or widen the panel',
                                    [Bbox.union([a.bbox, b.bbox])]))
                continue
            issues.append(Issue('text_overlap', 'error', f'{a.desc} overlaps {b.desc}', [a.bbox, b.bbox]))


def _check_text_clipped(texts, tol, issues, canvas, tight, **_):
    for t in texts:
        if _ignored(t.text, 'text_clipped'):
            continue
        bb = t.bbox
        if bb.x0 < canvas.x0 - tol or bb.y0 < canvas.y0 - tol or bb.x1 > canvas.x1 + tol or bb.y1 > canvas.y1 + tol:
            out = Bbox.intersection(bb, canvas)
            hidden = 1 - (out.width * out.height if out is not None else 0) / (bb.width * bb.height)
            hint = '' if tight else (" (bbox_inches='tight' keeps it, but then the saved figure is wider "
                                     "or taller than designed; check with tight=True)")
            issues.append(Issue('text_clipped', 'error',
                                f'{t.desc} is {hidden:.0%} outside the figure and will be cut off{hint}', [bb]))
            continue
        if t.text.get_clip_on() and t.text.get_clip_box() is not None:
            cb = t.text.get_clip_box()
            inside = Bbox.intersection(bb, cb)
            if inside is None or inside.width < bb.width - tol or inside.height < bb.height - tol:
                issues.append(Issue('text_clipped', 'error',
                                    f'{t.desc} is partly hidden by the axes clipping (clip_on=True)', [bb]))


def _check_text_over_data(fig, texts, dpi, tol, issues, **_):
    for t in texts:
        if t.kind not in ('annotation', 'figure') or _ignored(t.text, 'text_over_data') or _has_solid_bbox(t.text):
            continue
        bb = _shrink(t.bbox, tol)
        color = t.text.get_color()
        for ax in fig.axes:
            if not ax.get_visible() or not ax.bbox.overlaps(t.bbox):
                continue
            spines = [s for s in ax.spines.values() if s.get_visible()]
            for art in [*_data_artists(ax), *spines]:
                if _ignored(art, 'text_over_data'):
                    continue
                if art in spines:   # touching an axis line already reads badly: no tolerance
                    hit = _hits_data(t.bbox.padded(art.get_linewidth() * dpi / 72 / 2), art, dpi)
                else:
                    hit = _hits_data(bb, art, dpi)
                if hit is not None and art in spines:
                    issues.append(Issue('text_over_data', 'warning',
                                        f'{t.desc} crosses the axis line of {_axes_name(fig, ax)}', [t.bbox]))
                    break
                if hit is None:
                    continue
                if isinstance(hit, tuple):     # sits on a filled area: only a problem at low contrast
                    c = pcolors.contrast(color, hit[1])
                    if c < 3:
                        issues.append(Issue('text_over_data', 'warning',
                                            f'{t.desc} sits on a {to_hex(hit[1])} fill with contrast {c:.1f}:1 '
                                            '(< 3): move it or change the text colour', [t.bbox]))
                        break
                    continue
                label = art.get_label()
                what = f'{hit} of "{_short(label)}"' if label and not label.startswith('_') else hit
                issues.append(Issue('text_over_data', 'warning',
                                    f'{t.desc} overlaps a {what} in {_axes_name(fig, ax)}', [t.bbox]))
                break


def _legends(fig):
    for ax in fig.axes:
        if ax.get_legend() is not None and ax.get_legend().get_visible():
            yield ax.get_legend()
    yield from (l for l in fig.legends if l.get_visible())


def _check_legend_over_data(fig, dpi, tol, issues, renderer, **_):
    for leg in _legends(fig):
        if _ignored(leg, 'legend_over_data'):
            continue
        bb = _shrink(leg.get_window_extent(renderer), tol)
        for ax in fig.axes:
            if not ax.get_visible() or not ax.bbox.overlaps(bb):
                continue
            hits = [a for a in _data_artists(ax) if not _ignored(a, 'legend_over_data')
                    and (h := _hits_data(bb, a, dpi)) is not None and not isinstance(h, tuple)]
            if hits:
                issues.append(Issue('legend_over_data', 'warning',
                                    f'the legend covers data in {_axes_name(fig, ax)}: move it '
                                    '(loc=, bbox_to_anchor=) or label the lines directly', [bb]))
                break


def _check_font_size(j, texts, scale, issues, **_):
    small, large = {}, {}
    for t in texts:
        if _ignored(t.text, 'font_size'):
            continue
        size = t.text.get_fontsize() * scale
        if size < j.min_font - 1e-6:
            small.setdefault(round(size, 1), []).append(t)
        elif size > j.max_font + 1e-6:
            large.setdefault(round(size, 1), []).append(t)
    for size, ts in sorted(small.items()):
        issues.append(Issue('font_size', 'error',
                            f'{len(ts)} text(s) print at {size:g} pt, below the {j.name} minimum '
                            f'{j.min_font:g} pt: e.g. {_examples(ts)}', [t.bbox for t in ts]))
    for size, ts in sorted(large.items()):
        issues.append(Issue('font_size', 'info',
                            f'{len(ts)} text(s) print at {size:g} pt, above the usual {j.name} maximum '
                            f'{j.max_font:g} pt: e.g. {_examples(ts)}', [t.bbox for t in ts]))


def _examples(ts, n=3):
    return '; '.join(t.desc for t in ts[:n]) + (f' (+{len(ts) - n} more)' if len(ts) > n else '')


def _check_font_family(j, texts, issues, **_):
    off = {}
    for t in texts:
        if t.text.get_text().startswith('$') or _ignored(t.text, 'font_family'):
            continue
        name = t.text.get_fontname()
        if name not in j.fonts:
            off.setdefault(name, []).append(t)
    for name, ts in off.items():
        issues.append(Issue('font_family', 'info',
                            f'{len(ts)} text(s) set in {name}; {j.name} asks for {" or ".join(j.fonts[:2])} '
                            '(install the font or use pp.use(), which picks the first one available)'))


def _check_line_width(fig, j, scale, issues, **_):
    thin = {}

    def add(lw, what, ax):
        lw_print = lw * scale
        if 0 < lw_print < j.min_linewidth - 1e-6:
            thin.setdefault((round(lw_print, 2), what), set()).add(_axes_name(fig, ax))

    for ax in fig.axes:
        if not ax.get_visible():
            continue
        for a in _data_artists(ax):
            if _ignored(a, 'line_width'):
                continue
            if isinstance(a, Line2D) and a.get_linestyle() not in ('None', '', ' '):
                add(a.get_linewidth(), 'data line', ax)
            elif isinstance(a, LineCollection):
                for lw in set(np.atleast_1d(a.get_linewidth())):
                    add(lw, 'line collection', ax)
            elif isinstance(a, Patch) and to_rgba(a.get_edgecolor())[3] > 0 and a.get_linewidth() > 0 \
                    and to_rgba(a.get_facecolor())[3] == 0:
                add(a.get_linewidth(), 'outline', ax)
        for side, sp in ax.spines.items():
            if sp.get_visible():
                add(sp.get_linewidth(), 'axis line', ax)
        for axis in (ax.xaxis, ax.yaxis):
            ticks = axis.get_major_ticks()
            if ticks and ticks[0].tick1line.get_visible() and ticks[0].tick1line.get_markersize() > 0:
                add(ticks[0].tick1line.get_markeredgewidth(), 'tick', ax)
            if ticks and ticks[0].gridline.get_visible():
                add(ticks[0].gridline.get_linewidth(), 'grid line', ax)
    for (lw, what), where in sorted(thin.items()):
        severity = 'info' if what == 'grid line' else 'warning'
        issues.append(Issue('line_width', severity,
                            f'{what}s print at {lw:g} pt, thinner than the {j.name} minimum '
                            f'{j.min_linewidth:g} pt ({", ".join(sorted(where))})'))


def _check_contrast(fig, texts, issues, **_):
    low = {}
    for t in texts:
        if _ignored(t.text, 'contrast'):
            continue
        rgba = to_rgba(t.text.get_color(), t.text.get_alpha())
        bg = to_hex(_background(t.text, fig))
        # blend the text over its background when it is transparent
        rgb = np.array(rgba[:3]) * rgba[3] + np.array(to_rgba(bg)[:3]) * (1 - rgba[3])
        c = pcolors.contrast(rgb, bg)
        if c < 3:
            low.setdefault((to_hex(rgb), bg, round(c, 1)), []).append(t)
    for (color, bg, c), ts in low.items():
        issues.append(Issue('contrast', 'warning',
                            f'{len(ts)} text(s) in {color} on {bg} have contrast {c:g}:1 (< 3:1), hard to read '
                            f'in print; {_darker(color, bg)} or darker reaches 3:1. E.g. {_examples(ts)}',
                            [t.bbox for t in ts]))


def _darker(color, bg, target=3.0):
    """The lightest shade of `color` (mixed towards black, or white on dark backgrounds)
    with at least `target` contrast against bg."""
    rgb, ink = np.array(to_rgba(color)[:3]), (0.0 if pcolors.luminance(bg) > 0.5 else 1.0)
    for k in np.linspace(0, 1, 101):
        mixed = rgb * (1 - k) + ink * k
        if pcolors.contrast(mixed, bg) >= target:
            return to_hex(mixed)
    return to_hex([ink] * 3)


def _artist_colors(a):
    """The categorical colours of a data artist (empty for colormapped ones)."""
    if a.get_gid() == HIGHLIGHT_GID or _ignored(a, 'colors'):
        return []
    if isinstance(a, Line2D):
        return [a.get_color()] if a.get_linestyle() not in ('None', '', ' ') else [a.get_markerfacecolor()]
    if hasattr(a, 'get_array') and a.get_array() is not None:
        return []
    if isinstance(a, LineCollection):
        return list(a.get_color())
    if hasattr(a, 'get_facecolor'):
        fc = a.get_facecolor()
        fc = [fc] if isinstance(fc, tuple) else list(fc)
        return [c for c in fc if to_rgba(c)[3] > 0.1]
    return []


def _check_colors(fig, issues, **_):
    found = []
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        for a in _data_artists(ax):
            for c in _artist_colors(a):
                rgba = to_rgba(c)
                if rgba[3] <= 0.1 or min(rgba[:3]) > 0.95:   # transparent or white
                    continue
                found.append(to_hex(rgba[:3]))
    uniq = list(dict.fromkeys(found))
    if len(uniq) > 12:
        return   # many colours: a continuous encoding, not categories
    if len([c for c in uniq if pcolors.chroma(c) > 0.03]) > 8:
        issues.append(Issue('colors', 'info',
                            f'{len(uniq)} distinct colours: more than ~8 categories are hard to tell apart; '
                            'group the rest as "other", use small multiples, or label directly'))
    for c1, c2, what, d in pcolors.check_palette(uniq, normal_min=10, cvd_min=6):
        if what == 'normal':
            issues.append(Issue('colors', 'warning',
                                f'{c1} and {c2} look alike even with normal colour vision (dE {d:.1f} < 10)'))
        else:
            issues.append(Issue('colors', 'warning',
                                f'{c1} and {c2} look alike with {what} (dE {d:.1f} < 6): '
                                'change one, or add markers, line styles or direct labels'))


def _check_colormap(fig, issues, **_):
    names = set()
    for a in fig.findobj(lambda a: isinstance(a, mpl.cm.ScalarMappable)):
        cmap = getattr(a, 'cmap', None)
        if cmap is not None and getattr(a, 'get_array', lambda: None)() is not None:
            base = cmap.name.removesuffix('_r').lower()
            if base in RAINBOW_CMAPS:
                names.add(cmap.name)
    for name in sorted(names):
        issues.append(Issue('colormap', 'warning',
                            f'colormap "{name}" is not perceptually uniform and fails for colour-blind '
                            'readers: use viridis/cividis (sequential) or a two-hue diverging map'))


_VARNAME = re.compile(r'^[A-Za-z][A-Za-z0-9]*(_[A-Za-z0-9]+)+$')


def _check_labels(fig, texts, issues, **_):
    drawn = {id(t.text) for t in texts}
    for ax in fig.axes:
        if not ax.get_visible() or not ax.axison or _ignored(ax, 'labels'):
            continue
        has_data = bool(ax.lines or ax.collections or ax.patches or ax.images)
        if not has_data:
            continue
        name = _axes_name(fig, ax)
        for axis, xy in ((ax.xaxis, 'x'), (ax.yaxis, 'y')):
            label = axis.label.get_text()
            ticks_drawn = any(id(t) in drawn for t in axis.get_ticklabels())
            if not label and ticks_drawn and _numeric_ticks(axis) and not _shared_label(ax, xy):
                issues.append(Issue('labels', 'info', f'{xy}-axis of {name} has tick labels but no axis label'))
            elif _VARNAME.match(label):
                issues.append(Issue('labels', 'info',
                                    f'{xy} label "{label}" of {name} looks like a variable name; '
                                    'write it for the reader, with units'))
        handles, labels = ax.get_legend_handles_labels()
        if len(labels) >= 2 and ax.get_legend() is None and not fig.legends and not ax.texts:
            issues.append(Issue('labels', 'warning',
                                f'{name} has {len(labels)} labelled series but no legend or direct labels'))


def _numeric_ticks(axis):
    """True when the tick labels are numbers (category names label themselves)."""
    labels = [t.get_text() for t in axis.get_ticklabels() if t.get_text().strip()]
    return bool(labels) and all(re.fullmatch(r'[\s$\\{}^+\-\u2212\d.,eE%×x]*', l) for l in labels)


def _shared_label(ax, xy):
    """True when a neighbour sharing this axis carries the label (as in sharex grids)."""
    group = ax.get_shared_x_axes() if xy == 'x' else ax.get_shared_y_axes()
    return any((o.xaxis if xy == 'x' else o.yaxis).label.get_text() for o in group.get_siblings(ax) if o is not ax)
