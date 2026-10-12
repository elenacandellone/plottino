"""save(): check the figure, then write it at its exact size with embedded fonts."""
import re
from pathlib import Path

import matplotlib as mpl

from .checks import FigureCheckError, check, clear_highlights

VECTOR = {'pdf', 'svg', 'eps'}


def save(fig, path, formats=None, dpi=None, journal=None, width=None, run_check=True, strict=False,
         overlay=True, quiet=False, **savefig_kwargs):
    """Check `fig` and save it.

    path: 'plots/fig1.pdf' saves one file; 'plots/fig1' saves every format in `formats`
        (default pdf + png).
    dpi: raster resolution (default: the journal's).
    journal, width: as in check(); width is the printed width if it differs from the figure's.
    strict: raise FigureCheckError, and save nothing, when the check finds errors.
    overlay: when there are errors or warnings, also write <name>.check.png with the
        problem areas boxed and numbered as in the report.
    The figure is saved at its own size (no bbox_inches='tight' unless you pass it), so
    the printed width stays the one it was designed for.
    Returns the Report (None when run_check=False).
    """
    path = Path(path)
    if path.suffix:
        stem, formats = path.with_suffix(''), [path.suffix.lstrip('.')]
    else:
        stem, formats = path, list(formats or ('pdf', 'png'))
    stem.parent.mkdir(parents=True, exist_ok=True)

    report = None
    if run_check:
        tight = savefig_kwargs.get('bbox_inches') == 'tight'
        report = check(fig, journal=journal, width=width, tight=tight)
        if not quiet and report.issues:
            print(report)
        if strict and not report.ok:
            raise FigureCheckError(f'not saved, fix the errors first:\n{report}')
        if overlay and (report.errors or report.warnings):
            report.highlight()
            fig.savefig(f'{stem}.check.png', dpi=200, bbox_inches=savefig_kwargs.get('bbox_inches'))
            clear_highlights(fig)
            if not quiet:
                print(f'  problem areas boxed in {stem}.check.png')
    j = report.journal if report else None
    rc = {'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none'}
    with mpl.rc_context(rc):
        for fmt in formats:
            kw = dict(savefig_kwargs)
            if fmt not in VECTOR:
                kw.setdefault('dpi', dpi or (j.dpi if j else 600))
            fig.savefig(f'{stem}.{fmt}', format=fmt, **kw)
    spec = width if isinstance(width, str) else getattr(fig, '_paperplot_width', None)
    m = spec and re.fullmatch(r'\s*([0-9]*\.?[0-9]*)\s*\\?(textwidth|linewidth|columnwidth)\s*', spec)
    if m and not quiet:
        print(f'  LaTeX: \\includegraphics[width={m.group(1)}\\{m.group(2)}]{{{stem.name}}}')
    return report
