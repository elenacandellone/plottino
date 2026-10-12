"""Styles: journal sizes plus an optional decluttered look, applied to matplotlib and seaborn."""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

from . import journals
from .colors import OKABE_ITO, TEXT, LIGHT

_state = {'journal': journals.get('generic')}


def current_journal() -> journals.Journal:
    """The journal set by the last `use()` call (Generic before any call)."""
    return _state['journal']


def _available_font(candidates):
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in have:
            return name
    return 'DejaVu Sans'


def rc(journal='generic', declutter=True) -> dict:
    """The rcParams for a journal, without applying them (use with plt.rc_context)."""
    j = journals.get(journal)
    s = j.font_size
    lw = max(j.min_linewidth, 0.6)
    params = {
        'font.family': 'sans-serif',
        'font.sans-serif': [_available_font(j.fonts), *j.fonts],
        'font.size': s,
        'axes.titlesize': s + 1, 'axes.labelsize': s,
        'xtick.labelsize': s, 'ytick.labelsize': s,
        'legend.fontsize': s, 'legend.title_fontsize': s,
        'figure.titlesize': s + 1,
        'axes.linewidth': lw, 'grid.linewidth': lw,
        'xtick.major.width': lw, 'ytick.major.width': lw,
        'xtick.minor.width': lw, 'ytick.minor.width': lw,
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'lines.linewidth': 1.0, 'lines.markersize': 4,
        'patch.linewidth': lw,
        'axes.prop_cycle': mpl.cycler(color=OKABE_ITO),
        'figure.dpi': 150, 'savefig.dpi': j.dpi,
        'figure.constrained_layout.use': True,
        'pdf.fonttype': 42, 'ps.fonttype': 42,  # embed TrueType fonts, editable text
        'svg.fonttype': 'none',
        'legend.frameon': False,
        'axes.titlelocation': 'left',
        'mathtext.default': 'regular',
    }
    if declutter:
        params.update({
            'axes.spines.top': False, 'axes.spines.right': False,
            'text.color': TEXT, 'axes.labelcolor': TEXT, 'axes.edgecolor': TEXT,
            'xtick.color': TEXT, 'ytick.color': TEXT,
            'axes.grid': True, 'grid.color': LIGHT, 'axes.axisbelow': True,
        })
    return params


def use(journal='generic', declutter=True, seaborn=True):
    """Apply a journal preset globally (and to seaborn's theme when seaborn is installed).

    Seaborn's own theme is set first, so that the journal sizes override it.
    """
    j = journals.get(journal)
    if seaborn:
        try:
            import seaborn as sns
            sns.set_theme(context='paper', style='ticks', palette=OKABE_ITO)
        except ImportError:
            pass
    mpl.rcParams.update(rc(j, declutter))
    _state['journal'] = j
    return j


def use_latex(textwidth='article', fontsize=10, columnwidth=None, declutter=True, seaborn=True):
    """Style figures for a LaTeX document; widths become fractions of its text width.

        pp.use_latex()                          # Overleaf article, 10pt
        pp.use_latex(textwidth=r'6.5in', fontsize=11)
        fig, ax = pp.figure(r'0.5\\textwidth')  # include with width=0.5\\textwidth

    See paperplot.journals.latex for the arguments.
    """
    return use(journals.latex(textwidth, fontsize, columnwidth), declutter, seaborn)


def figure(width=None, height=None, aspect=0.62, journal=None, nrows=1, ncols=1, **kwargs):
    """plt.subplots at the final printed size.

    width: inches, a column name ('single', 'double'), or a fraction of one such as
    r'0.5\\textwidth' after use_latex(). Defaults to the journal's first width.
    height defaults to width * aspect. Extra keyword arguments go to plt.subplots.
    """
    j = journals.get(journal) if journal is not None else current_journal()
    if width is None:
        width = next(iter(j.widths))
    w = j.width(width)
    h = height if height is not None else w * aspect
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    fig._paperplot_journal = j
    if isinstance(width, str):
        fig._paperplot_width = width
    return fig, axes
