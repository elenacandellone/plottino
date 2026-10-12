# paperplot

Paper-ready figures with matplotlib and seaborn. paperplot sets the figure to the size
it will be printed at, styles it for the journal (or your LaTeX document), and then
**checks that it is legible**: no overlapping or cut-off labels, no text under data,
no fonts or lines too small to print, no colours that colour-blind readers cannot tell
apart.

```python
import paperplot as pp
import seaborn as sns

pp.use('science')                      # journal sizes + a decluttered style (also sets seaborn)
fig, ax = pp.figure('double', aspect=0.5)
sns.lineplot(data=df, x='year', y='value', hue='group', ax=ax)
ax.set(xlabel='Year', ylabel='Value (EUR)')
pp.save(fig, 'plots/fig1')             # checks, then writes fig1.pdf and fig1.png
```

```
paperplot check: Science, figure 4.76 x 2.38 in
  x error   text_overlap     x tick labels overlap in axes 0: use fewer ticks, rotate them or widen the panel
  ! warning legend_over_data the legend covers data in axes 0: move it (loc=, bbox_to_anchor=) or label the lines directly
  ! warning colors           #d62728 and #2ca02c look alike with deuteranopia (dE 4.1 < 6): change one, or add markers, line styles or direct labels
  1 error, 2 warnings
  problem areas boxed in plots/fig1.check.png
```

## LaTeX / Overleaf documents

Size figures as a fraction of the text width, as you would in `\includegraphics`:

```python
pp.use_latex()                              # Overleaf default: article, 10pt (\textwidth = 345pt)
pp.use_latex(textwidth='a4-1in', fontsize=11)   # geometry with 1in margins on A4
pp.use_latex(textwidth=418.25)              # the value \the\textwidth prints in your document
pp.use_latex(textwidth=505, columnwidth=241)    # two-column: also \linewidth / \columnwidth

fig, ax = pp.figure(r'0.5\textwidth')       # made at exactly half the text width
pp.save(fig, 'fig2')                        # prints: \includegraphics[width=0.5\textwidth]{fig2}
```

The figure is built at its printed size and its text at the document's `\footnotesize`
(8 pt in a 10 pt document), so LaTeX does not shrink anything: what you set is what is
printed. A figure made at another size can still be checked at the size it will be used:
`pp.check(fig, width=r'0.5\textwidth')` scales fonts and lines accordingly and flags any
that become too small.

## What is checked

| check | finds |
|---|---|
| `size` | width not one of the journal's column widths; height over the page maximum |
| `text_overlap` | text overlapping text: crowded tick labels, labels on labels, annotations (rotation-aware) |
| `text_clipped` | text cut off at the figure edge or hidden by axes clipping |
| `text_over_data` | annotations on lines or markers, or on fills with too little contrast |
| `legend_over_data` | a legend box covering lines or points |
| `font_size` | text below the journal minimum at print size (above its maximum: info) |
| `font_family` | text not in the journal's fonts (info) |
| `line_width` | lines, ticks and axes thinner than the journal minimum at print size |
| `contrast` | text whose colour is too close to its background (WCAG ratio < 3) |
| `colors` | data colours hard to tell apart, with normal vision or simulated protanopia, deuteranopia or tritanopia |
| `colormap` | rainbow colormaps (jet, hsv, ...) |
| `labels` | axes without labels, labels like `mean_auc_score`, several series without a legend |

Checks run on what matplotlib actually draws, so they work on any matplotlib or seaborn
figure. Use them directly:

```python
report = pp.check(fig)             # or pp.check(fig, journal='nature', width='single')
print(report); report.ok           # ok = no errors
report.highlight()                 # numbered red boxes on the figure; pp.clear_highlights(fig)
report.raise_for_errors()          # e.g. in a test or CI
pp.ignore(text, 'text_over_data')  # a label that sits on a bar on purpose
pp.check(fig, skip=['font_family'])
```

`pp.save(fig, path, strict=True)` refuses to save a figure with errors.

**Saving with `bbox_inches='tight'`** keeps text that sticks out of the figure, but the
saved file is then wider than designed, and shrinks when placed at the column width.
`pp.save(fig, path, bbox_inches='tight')` (or `pp.check(fig, tight=True)`) checks the tight
canvas and reports the resulting scale, e.g. a 6 pt footnote that prints at 5.7 pt.

## Journal presets

`science`, `nature`, `pnas`, `cell`, `generic`, plus `pp.latex(...)` for any LaTeX document.
Each preset records its source page: guidelines change, so check them before submitting.

| | widths | text | min line |
|---|---|---|---|
| Science | 5.7 / 12.1 / 18.4 cm | >= 6 pt | 0.5 pt |
| Nature | 89 / 183 mm, max height 170 mm | 5-7 pt | 0.25 pt |
| PNAS | 8.7 / 11.4 / 17.8 cm | 6-8 pt | 0.5 pt |
| Cell | 85 / 114 / 174 mm | >= 6 pt | 0.5 pt |

Add your own with `pp.journals.register('mykey', pp.Journal(...))`.

## Helpers

- `pp.panel_labels(axes)`: bold A, B, C (or a, b, c for Nature) at the panel corners
- `pp.label_lines(ax)`: label lines at their right end instead of a legend, nudged apart
- `pp.emphasize(ax, keep=['treated'])`: grey out everything but the series that carry the message
- `pp.OKABE_ITO`: the default colour-blind-safe palette; `pp.GREY`, `pp.LIGHT`, `pp.TEXT`
- `pp.colors.check_palette([...])`: colour pairs that are hard to tell apart

## Examples

[examples/examples.ipynb](examples/examples.ipynb): a LaTeX figure, checking and highlighting
problems, the fixed version, journal presets with seaborn, rescaling, palettes and saving.
[examples/latex_example.py](examples/latex_example.py): the same as a script.

## Install

```
pip install -e .            # from a clone
pip install -e '.[test]' && pytest
```

## References

- Okabe & Ito (2008), *Color Universal Design*: the default palette.
- Machado, Oliveira & Fernandes (2009), *A physiologically-based model for simulation of
  color vision deficiency*, IEEE TVCG 15(6): colour-blindness simulation.
- Ottosson (2020), *A perceptual color space for image processing* (OKLab): colour distances.
- WCAG 2.1 contrast ratio: text contrast.
