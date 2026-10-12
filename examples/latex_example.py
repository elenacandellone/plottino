"""A seaborn figure for an Overleaf article, at half the text width: first with common
mistakes, then fixed. Run: python examples/latex_example.py (writes to examples/out/)."""
import numpy as np
import pandas as pd
import seaborn as sns

import paperplot as pp

rng = np.random.default_rng(0)
years = np.arange(2000, 2021)
df = pd.DataFrame({
    'year': np.tile(years, 3),
    'value_eur': np.concatenate([np.cumsum(rng.normal(1, 1, len(years))) + k * 3 for k in range(3)]),
    'group': np.repeat(['control', 'treated early', 'treated late'], len(years)),
})

pp.use_latex()                       # Overleaf article, 10pt: \textwidth = 345pt

# --- with mistakes: red/green, legend on the data, tiny annotation, label = column name
fig, ax = pp.figure(r'0.5\textwidth', aspect=0.75)
sns.lineplot(data=df, x='year', y='value_eur', hue='group', palette=['#d62728', '#2ca02c', '#1f77b4'], ax=ax)
ax.legend(loc='upper left')
ax.text(2001, 10, 'policy change', fontsize=4)
pp.save(fig, 'examples/out/before')

# --- fixed: colour-blind-safe palette, direct labels, readable sizes, labels for the reader
fig, ax = pp.figure(r'0.5\textwidth', aspect=0.75)
sns.lineplot(data=df, x='year', y='value_eur', hue='group', legend=False, ax=ax)
for line, name in zip(ax.lines, ['control', 'treated early', 'treated late']):
    line.set_label(name)
pp.label_lines(ax)
ax.axvline(2010, color=pp.GREY, lw=0.8, ls=':')
ax.text(2010.3, 1, 'policy change', color='#6e6e6e', va='bottom')
ax.set(xlabel='Year', ylabel='Value (EUR)', xticks=[2000, 2010, 2020])
pp.save(fig, 'examples/out/after')
