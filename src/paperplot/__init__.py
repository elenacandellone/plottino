"""paperplot: paper-ready matplotlib/seaborn figures, with checks that they are legible.

    import paperplot as pp
    pp.use('science')                       # or pp.use_latex() for an Overleaf document
    fig, ax = pp.figure('double')           # or pp.figure(r'0.5\\textwidth')
    ...
    pp.save(fig, 'plots/fig1')              # checks, then writes fig1.pdf + fig1.png
"""
from . import colors, journals
from .checks import ALL_CHECKS, FigureCheckError, Issue, Report, check, clear_highlights, ignore
from .colors import GREY, LIGHT, OKABE_ITO, TEXT
from .export import save
from .helpers import emphasize, label_lines, panel_labels
from .journals import JOURNALS, Journal, latex
from .style import current_journal, figure, rc, use, use_latex

__version__ = '0.1.0'

__all__ = ['use', 'use_latex', 'rc', 'figure', 'current_journal', 'check', 'save', 'ignore',
           'clear_highlights', 'Report', 'Issue', 'FigureCheckError', 'ALL_CHECKS',
           'panel_labels', 'emphasize', 'label_lines', 'Journal', 'JOURNALS', 'latex',
           'colors', 'journals', 'OKABE_ITO', 'GREY', 'LIGHT', 'TEXT']
