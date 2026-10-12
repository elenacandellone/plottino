"""Make the before/after images in the README (docs/img/). Run from the repo root:

    python examples/readme_figures.py

Each "before" is saved with plottino's highlights (numbered red boxes); each "after" must pass
the check with no errors or warnings.
"""
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import plottino as pt

OUT = Path('docs/img')
PX = 900   # width of every image in pixels, so pairs are shown at the same scale


def save(fig, name, report=None):
    """Save at PX pixels wide: a figure wider than its column is shown shrunk, as in print."""
    if report is not None:
        report.highlight()
    fig.savefig(OUT / f'{name}.png', dpi=PX / fig.get_figwidth(), facecolor='white')
    plt.close(fig)


def check_before(fig, name, **kw):
    report = pt.check(fig, **kw)
    print(f'--- {name}\n{report}\n')
    assert report.errors or report.warnings, f'{name}: expected problems'
    return report


def check_after(fig, name, **kw):
    report = pt.check(fig, **kw)
    print(f'--- {name}\n{report}\n')
    assert report.ok and not report.warnings, f'{name}: should be clean'


def crowded_labels():
    pt.use('science')
    countries = ['Netherlands', 'Germany', 'Belgium', 'Luxembourg', 'Switzerland', 'Liechtenstein']
    values = [42, 37, 31, 22, 18, 9]

    fig, ax = pt.figure('single', aspect=0.8)
    ax.bar(countries, values, color=pt.OKABE_ITO[0])
    ax.set(xlabel='Country', ylabel='Cases')
    save(fig, 'labels_before', check_before(fig, 'labels before'))

    fig, ax = pt.figure('single', aspect=0.8)
    ax.barh(countries[::-1], values[::-1], color=pt.OKABE_ITO[0])
    ax.set(xlabel='Cases')
    ax.grid(axis='y', visible=False)
    check_after(fig, 'labels after')
    save(fig, 'labels_after')


def legend_and_colours():
    pt.use_latex()
    rng = np.random.default_rng(3)
    years = np.arange(2000, 2021)
    series = {name: np.cumsum(rng.normal(1, 0.8, len(years))) + k * 4
              for k, name in enumerate(['control', 'treated early', 'treated late'])}

    fig, ax = pt.figure(r'0.5\textwidth', aspect=0.75)
    for (name, y), c in zip(series.items(), ['#d62728', '#2ca02c', '#1f77b4']):
        ax.plot(years, y, label=name, color=c)
    ax.legend(loc='upper left')
    ax.set(xlabel='year', ylabel='value_eur')
    save(fig, 'legend_before', check_before(fig, 'legend before'))

    fig, ax = pt.figure(r'0.5\textwidth', aspect=0.75)
    for name, y in series.items():
        ax.plot(years, y, label=name)
    pt.label_lines(ax)
    ax.set(xlabel='Year', ylabel='Value (EUR)', xticks=[2000, 2010, 2020])
    check_after(fig, 'legend after')
    save(fig, 'legend_after')


def shrunk_figure():
    pt.use('pnas')
    rng = np.random.default_rng(1)
    groups = np.repeat(['A', 'B', 'C', 'D'], 40)
    scores = np.concatenate([rng.normal(m, 1, 40) for m in (0, 0.5, 1.2, 2)])

    # matplotlib defaults, made at full page width on screen, then placed in a single column
    with plt.style.context('default'):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.boxplot(x=groups, y=scores, ax=ax, color=pt.OKABE_ITO[4])
        ax.set(xlabel='Group', ylabel='Score (a.u.)')
        save(fig, 'shrunk_before', check_before(fig, 'shrunk before', width='single'))

    fig, ax = pt.figure('single', aspect=0.65)
    sns.boxplot(x=groups, y=scores, ax=ax, color=pt.OKABE_ITO[4], linewidth=0.8, fliersize=2)
    ax.set(xlabel='Group', ylabel='Score (a.u.)')
    check_after(fig, 'shrunk after')
    save(fig, 'shrunk_after')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    crowded_labels()
    legend_and_colours()
    shrunk_figure()
    print(f'-> {OUT}/')
