"""Figure specifications of journals: widths, heights, font and line sizes at print size.

All lengths are in inches, font sizes and line widths in points (1 pt = 1/72 in).
Each preset records the page it was taken from; check it again before submitting,
journals change their guidelines.
"""
import re
from dataclasses import dataclass

MM = 1 / 25.4      # inches per millimetre
TEX_PT = 1 / 72.27  # inches per TeX point (\the\textwidth reports TeX points)


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


JOURNALS = {
    'science': Journal(
        name='Science',
        widths={'single': 57 * MM, 'double': 121 * MM, 'triple': 184 * MM},  # 2.24 / 4.76 / 7.24 in
        max_height=9.0, min_font=6.0, font_size=7.0, max_font=9.0, min_linewidth=0.5,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='upper',
        source='https://www.science.org/content/page/instructions-preparing-initial-manuscript',
        notes='widths from the page above; min font / line width are common print rules, not quoted from Science',
    ),
    'nature': Journal(
        name='Nature',
        widths={'single': 89 * MM, 'double': 183 * MM},
        max_height=170 * MM, min_font=5.0, font_size=7.0, max_font=7.0, min_linewidth=0.25,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='lower',
        source='https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/',
        notes='text 5-7 pt, lines 0.25-1 pt, max height 170 mm',
    ),
    'pnas': Journal(
        name='PNAS',
        widths={'single': 87 * MM, 'onehalf': 114 * MM, 'double': 178 * MM},
        max_height=230 * MM, min_font=6.0, font_size=7.0, max_font=8.0, min_linewidth=0.5,
        fonts=('Arial', 'Helvetica', 'DejaVu Sans'), panel_label_case='upper',
        source='https://www.pnas.org/author-center/submitting-your-manuscript',
        notes='text 6-8 pt Helvetica or Arial',
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
    try:
        return JOURNALS[journal.lower()]
    except KeyError:
        raise ValueError(f'unknown journal {journal!r}; choose from {list(JOURNALS)} '
                         'or pass a paperplot.Journal') from None


def register(key: str, journal: Journal):
    """Add a custom journal preset, usable by name afterwards."""
    JOURNALS[key.lower()] = journal
