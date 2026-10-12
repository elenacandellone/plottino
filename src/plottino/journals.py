"""Figure specifications of journals: widths, heights, font and line sizes at print size.

All lengths are in inches, font sizes and line widths in points (1 pt = 1/72 in).
Each preset records the page it was taken from; check it again before submitting,
journals change their guidelines.
"""
import re
from dataclasses import dataclass

MM = 1 / 25.4      # inches per millimetre
TEX_PT = 1 / 72.27  # inches per TeX point (\the\textwidth reports TeX points)
PICA = 1 / 6       # inches per pica (12 pt)


@dataclass(frozen=True)
class Journal:
    name: str
    widths: dict                     # column name -> width (in)
    max_height: float                # in
    min_font: float                  # pt, smallest allowed text at print size
    font_size: float                 # pt, default body text in the style
    max_font: float = 12.0           # pt, larger text is flagged as oversized
    min_linewidth: float = 0.25      # pt
    fonts: tuple = ('Arial', 'Helvetica', 'DejaVu Sans')
    panel_label_case: str = 'upper'  # 'upper' (A, B) or 'lower' (a, b)
    panel_label_size: float = None   # pt, bold panel letters (default: font_size + 1)
    min_marker: float = 0.0          # pt, smallest symbol (marker) size; 0 = not checked
    rules: tuple = ()                # house rules, see checks._check_journal_rules: 'no_figure_title',
                                     # 'no_minor_ticks', 'no_gridlines', 'axis_lines', 'units_in_labels',
                                     # 'no_colored_text'
    dpi: int = 600                   # raster export resolution
    source: str = ''
    notes: str = ''

    def width(self, w) -> float:
        """Resolve a width to inches: a number (inches), a column name ('single', 'double'),
        or a fraction of one, LaTeX style: r'0.5\\textwidth', '0.5 linewidth', '0.3 double'."""
        if not isinstance(w, str):
            return float(w)
        m = re.fullmatch(r'\s*([0-9]*\.?[0-9]*)\s*\\?([A-Za-z]+)\s*', w)
        if m and m.group(2) in self.widths:
            return float(m.group(1) or 1) * self.widths[m.group(2)]
        raise ValueError(f'{self.name}: unknown width {w!r}; use inches, one of {list(self.widths)}, '
                         'or a fraction such as "0.5 ' + next(iter(self.widths)) + '"')


# shared by the Science family of journals (Science Advances revision guide, 2026)
_SCIENCE_FAMILY = dict(
    min_font=6.0, font_size=8.0, max_font=8.0, min_linewidth=0.28, panel_label_size=9.0, min_marker=5.0,
    fonts=('Myriad Pro', 'Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='upper',
    rules=('no_figure_title', 'no_minor_ticks', 'units_in_labels'), dpi=600,
)

JOURNALS = {
    'science': Journal(
        name='Science',
        widths={'single': 57 * MM, 'double': 121 * MM, 'triple': 184 * MM},  # 2.24 / 4.76 / 7.24 in
        max_height=9.0, **_SCIENCE_FAMILY,
        source='https://www.science.org/content/page/instructions-preparing-initial-manuscript (widths); '
               'https://www.science.org/cms/asset/76887697-528f-4a22-afea-cee904504e76/sciadv_guide_to_preparing_figures_2026.pdf (type, lines, symbols)',
        notes='Science (3 columns). Text 8 pt (6-8 pt, min 6), panel letters 9 pt bold, lines >= 0.28 pt, '
              'symbols >= 5 pt, no figure titles in the image, no minor ticks; files above 600 dpi are '
              'downsampled to 600',
    ),
    'sciadv': Journal(
        name='Science Advances',
        widths={'single': 21.25 * PICA, 'onehalf': 34 * PICA, 'double': 43.5 * PICA},  # 21p3 / 34p / 43p6
        max_height=9.0, **_SCIENCE_FAMILY,
        source='https://www.science.org/cms/asset/76887697-528f-4a22-afea-cee904504e76/sciadv_guide_to_preparing_figures_2026.pdf',
        notes='2 columns; widths between single and double may not exceed 5.67 in (onehalf). Max depth 9 in, '
              '7.8 in recommended for double-column figures so the legend fits. Type and line rules as Science',
    ),
    'nature': Journal(
        name='Nature',
        widths={'single': 89 * MM, 'double': 183 * MM},
        max_height=170 * MM, min_font=5.0, font_size=7.0, max_font=7.0, min_linewidth=0.25,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='lower', panel_label_size=8.0,
        rules=('no_gridlines', 'axis_lines', 'units_in_labels', 'no_colored_text'), dpi=600,
        source='https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/ ; '
               'https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/',
        notes='text 5-7 pt Arial/Helvetica, panel letters 8 pt bold lowercase, lines 0.25-1 pt, max height '
              '170 mm; axis lines and ticks, units in parentheses, no background gridlines, no coloured text '
              '(use keys), fonts embedded (Type 42), images >= 450 dpi',
    ),
    'pnas': Journal(
        name='PNAS',
        widths={'single': 20.5 * PICA, 'onehalf': 27 * PICA, 'double': 42.125 * PICA},  # 3.42 / 4.5 / 7 in
        max_height=54 * PICA, min_font=6.0, font_size=7.0, max_font=8.0, min_linewidth=0.25,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='upper', dpi=600,
        source='https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf (Digital Art Guidelines, 2022)',
        notes='text 6-8 pt, at least 6 pt after reduction; same font in all figures (Arial, Helvetica, ...), '
              'embedded; graph lines >= 0.25 pt; max height 9 in; raster with text 600-900 ppi, line art '
              '1000-1200 ppi, vector preferred; no panel-letter style specified',
    ),
    'cell': Journal(
        name='Cell',
        widths={'single': 85 * MM, 'onehalf': 114 * MM, 'double': 174 * MM},
        max_height=230 * MM, min_font=6.0, font_size=7.0, max_font=12.0, min_linewidth=0.5,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='upper', dpi=1000,
        source='https://www.cell.com/figureguidelines',
        notes='Arial/Helvetica, 6-8 pt tick labels; 1000 dpi for line art',
    ),
    'generic': Journal(
        name='Generic',
        widths={'single': 3.5, 'onehalf': 5.0, 'double': 7.0},
        max_height=9.0, min_font=6.0, font_size=8.0, max_font=12.0, min_linewidth=0.5,
        source='', notes='safe defaults for journals without a preset',
    ),
}


# \textwidth of common LaTeX layouts, in TeX points. Print the real value of a document
# with \the\textwidth (or \the\columnwidth) and pass the number instead.
LATEX_TEXTWIDTHS = {
    'article': 345.0,        # article/report, 10pt (Overleaf default)
    'article-11pt': 360.0,
    'article-12pt': 390.0,
    'a4-1in': 159.2 * MM / TEX_PT,   # \usepackage[margin=1in]{geometry}, a4paper (6.27 in)
    'letter-1in': 6.5 / TEX_PT,      # \usepackage[margin=1in]{geometry}, letterpaper
    'a4-2.5cm': 160 * MM / TEX_PT,   # \usepackage[margin=2.5cm]{geometry}, a4paper
}
# font size of figure text relative to the document: \footnotesize of each base size
_FOOTNOTESIZE = {10: 8.0, 11: 9.0, 12: 10.0}


def latex(textwidth='article', fontsize=10, columnwidth=None) -> Journal:
    """A preset for a LaTeX document: widths are fractions of its \\textwidth.

    textwidth: a name from LATEX_TEXTWIDTHS, a number of TeX points (from \\the\\textwidth),
    or a string with a unit ('6.5in', '16cm', '345pt'). fontsize: the document's base size
    (10, 11, 12); figure text defaults to its \\footnotesize so it reads like a caption.
    columnwidth: for two-column documents (\\the\\columnwidth), same units as textwidth.
    Widths then accept r'0.5\\textwidth', r'\\linewidth' (= columnwidth if given) or
    r'0.8\\columnwidth'.
    """
    tw = _tex_length(textwidth)
    cw = _tex_length(columnwidth) if columnwidth is not None else tw
    body = float(fontsize)
    return Journal(
        name=f'LaTeX ({tw / TEX_PT:.0f}pt text, {fontsize:g}pt font)',
        widths={'textwidth': tw, 'linewidth': cw, 'columnwidth': cw},
        max_height=1.6 * tw, min_font=max(5.0, round(0.6 * body, 1)),
        font_size=_FOOTNOTESIZE.get(int(body), round(0.8 * body, 1)), max_font=body + 2,
        min_linewidth=0.3, dpi=600,
        notes='sized for \\includegraphics at the same width, so text prints at the size set here',
    )


def _tex_length(v) -> float:
    """A LaTeX length to inches: a preset name, a number (TeX points) or '<n><unit>'."""
    if isinstance(v, (int, float)):
        return v * TEX_PT
    if v in LATEX_TEXTWIDTHS:
        return LATEX_TEXTWIDTHS[v] * TEX_PT
    m = re.fullmatch(r'\s*([0-9.]+)\s*(pt|bp|in|cm|mm)\s*', v)
    if not m:
        raise ValueError(f'unknown LaTeX length {v!r}; use a number of pt, "6.5in", "16cm", '
                         f'or one of {list(LATEX_TEXTWIDTHS)}')
    n = float(m.group(1))
    return n * {'pt': TEX_PT, 'bp': 1 / 72, 'in': 1, 'cm': 10 * MM, 'mm': MM}[m.group(2)]


def get(journal) -> Journal:
    """Return a Journal from a name ('science', 'nature', ...) or pass a Journal through."""
    if isinstance(journal, Journal):
        return journal
    key = journal.lower()
    key = {'science-advances': 'sciadv', 'science advances': 'sciadv'}.get(key, key)
    try:
        return JOURNALS[key]
    except KeyError:
        raise ValueError(f'unknown journal {journal!r}; choose from {list(JOURNALS)} '
                         'or pass a plottino.Journal') from None


def register(key: str, journal: Journal):
    """Add a custom journal preset, usable by name afterwards."""
    JOURNALS[key.lower()] = journal
