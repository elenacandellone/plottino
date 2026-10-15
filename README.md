<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/logo/plottino-logo-dark.svg">
    <img src="docs/img/logo/plottino-logo-light.svg" alt="plottino" width="360">
  </picture>
</h1>

Paper-ready matplotlib and seaborn figures. plottino makes each figure at the size it will be
printed, styles it for the journal or your LaTeX document, and **checks that it is legible**.

```
pip install git+https://github.com/elenacandellone/plottino
```

```python
import plottino as pt

pt.use('science')                        # or 'nature', 'pnas', 'cell', 'sciadv'; or pt.use_latex()
fig, ax = pt.figure('single')            # or pt.figure(r'0.5\textwidth') after pt.use_latex()
...                                      # any matplotlib / seaborn plot
pt.save(fig, 'fig1')                     # checks, then writes fig1.pdf + fig1.png
```

```
plottino check: Science, figure 2.24 x 1.80 in
  x error   text_overlap     6 x tick labels overlap in axes 0: use fewer ticks, rotate them, swap the axes or widen the panel
```

## Before and after

Left: as figures often start, with the problems plottino finds boxed. Right: after following
its report. Shown at the same printed width ([code](examples/readme_figures.py)).

| | Before | After |
|---|:---:|:---:|
| Crowded labels | <img src="docs/img/labels_before.png" width="330"> | <img src="docs/img/labels_after.png" width="330"> |
| Legend on the data; red and green | <img src="docs/img/legend_before.png" width="330"> | <img src="docs/img/legend_after.png" width="330"> |
| Made at screen size, shrunk into a column | <img src="docs/img/shrunk_before.png" width="330"> | <img src="docs/img/shrunk_after.png" width="330"> |

## What it checks

Overlapping or cut-off text · text or legends on top of data · fonts, lines and symbols too
small at print size · figure size against the journal's columns · low-contrast text · colours
colour-blind readers cannot tell apart · rainbow colormaps · unlabelled axes · the journal's
own rules (e.g. no figure title in the image, no red with green, units in axis labels).

```python
report = pt.check(fig, journal='nature')   # print(report), report.ok, report.highlight()
pt.check(fig, width=r'0.5\textwidth')      # check at the size it will be included
pt.save(fig, 'fig1', strict=True)          # refuse to save a figure with errors
```

## Journals

| | widths | text | source |
|---|---|---|---|
| Science | 5.7 / 12.1 / 18.4 cm | 6-8 pt | [guide](https://www.science.org/cms/asset/76887697-528f-4a22-afea-cee904504e76/sciadv_guide_to_preparing_figures_2026.pdf) |
| Science Advances | 9 / 14.4 / 18.4 cm | 6-8 pt | [guide](https://www.science.org/cms/asset/76887697-528f-4a22-afea-cee904504e76/sciadv_guide_to_preparing_figures_2026.pdf) |
| Nature | 89 / 183 mm | 5-7 pt | [specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/) |
| PNAS | 8.7 / 11.4 / 17.8 cm | 6-8 pt | [guidelines](https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf) |
| Cell | 8.5 / 11.4 / 17.4 cm | 6-8 pt | [guidelines](https://www.cell.com/information-for-authors/figure-guidelines) |
| LaTeX | fractions of `\textwidth` | `\footnotesize` | `pt.use_latex(textwidth=..., fontsize=...)` |

Guidelines change: check them before submitting. Add your own with `pt.journals.register`.

Helpers: `pt.panel_labels`, `pt.label_lines` (direct labels instead of a legend),
`pt.emphasize` (grey out the rest), `pt.OKABE_ITO` (colour-blind-safe palette).
More in [examples/examples.ipynb](examples/examples.ipynb).

Colour-blindness simulation: Machado et al. (2009); colour distances: OKLab (Ottosson 2020);
palette: Okabe & Ito (2008).
