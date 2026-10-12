import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

import plottino as pt


@pytest.fixture(autouse=True)
def style():
    pt.use('science', seaborn=False)
    yield
    plt.close('all')


def checks_found(report, severity=None):
    return {i.check for i in report if severity is None or i.severity == severity}


def clean_figure():
    fig, ax = pt.figure('double', aspect=0.5)
    x = np.linspace(0, 10, 50)
    ax.plot(x, np.sin(x), label='sine')
    ax.plot(x, np.cos(x), label='cosine')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Signal (mV)')
    ax.legend(loc='upper right', bbox_to_anchor=(1, 1.25), ncols=2)
    return fig, ax


def test_clean_figure_has_no_errors_or_warnings():
    fig, _ = clean_figure()
    report = pt.check(fig)
    assert report.ok, report
    assert not report.warnings, report


def test_overlapping_tick_labels():
    fig, ax = pt.figure('single')
    ax.bar([f'category number {i}' for i in range(8)], range(8))
    ax.set_xlabel('Category'), ax.set_ylabel('Count')
    report = pt.check(fig)
    msgs = [i for i in report if i.check == 'text_overlap']
    assert len(msgs) == 1 and 'x tick labels overlap' in msgs[0].message


def test_rotated_tick_labels_do_not_false_positive():
    fig, ax = pt.figure('double')
    ax.bar([f'cat {i}' for i in range(6)], range(6))
    ax.tick_params(axis='x', rotation=45)
    ax.set_xlabel('Category'), ax.set_ylabel('Count')
    assert 'text_overlap' not in checks_found(pt.check(fig))


def test_text_overlap_between_annotations():
    fig, ax = clean_figure()
    ax.text(5, 0, 'first label here')
    ax.text(5.3, 0.02, 'second label')
    assert 'text_overlap' in checks_found(pt.check(fig), 'error')


def test_text_outside_figure():
    fig, ax = clean_figure()
    ax.text(1.02, 0.5, 'a long note that runs off the edge', transform=ax.transAxes, in_layout=False)
    report = pt.check(fig)
    assert 'text_clipped' in checks_found(report, 'error')


def test_text_over_line_and_ignore():
    fig, ax = clean_figure()
    t = ax.text(np.pi / 2, 1.0, 'peak', ha='center', va='center')
    assert 'text_over_data' in checks_found(pt.check(fig))
    pt.ignore(t, 'text_over_data')
    assert 'text_over_data' not in checks_found(pt.check(fig))


def test_text_with_background_box_is_fine():
    fig, ax = clean_figure()
    ax.text(np.pi / 2, 1.0, 'peak', ha='center', va='center', bbox=dict(fc='white', ec='none'))
    assert 'text_over_data' not in checks_found(pt.check(fig))


def test_text_on_dark_bar_low_contrast():
    fig, ax = pt.figure('single')
    ax.bar(['a', 'b'], [3, 4], color='#222222')
    ax.text(0, 1.5, 'n=3', ha='center', color='black')
    ax.set_xlabel('Group'), ax.set_ylabel('Value')
    msgs = [i.message for i in pt.check(fig) if i.check == 'text_over_data']
    assert msgs and 'contrast' in msgs[0]


def test_legend_over_data():
    fig, ax = pt.figure('single')
    x = np.linspace(0, 1, 100)
    for k in range(3):
        ax.plot(x, x * 0 + 0.9 - 0.02 * k, label=f'series {k}')
    ax.legend(loc='upper left')
    ax.set_xlabel('x'), ax.set_ylabel('y')
    assert 'legend_over_data' in checks_found(pt.check(fig))


def test_small_fonts_and_scaling():
    fig, ax = clean_figure()
    ax.set_xlabel('Time (s)', fontsize=4)
    assert 'font_size' in checks_found(pt.check(fig), 'error')
    # 7 pt text on a figure printed at half its width becomes 3.5 pt
    fig2, ax2 = clean_figure()
    report = pt.check(fig2, width=fig2.get_size_inches()[0] / 2)
    assert 'font_size' in checks_found(report, 'error')


def test_width_not_a_column():
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot([0, 1], [0, 1])
    assert 'size' in checks_found(pt.check(fig))


def test_too_tall():
    fig, ax = pt.figure('single', height=12)
    ax.plot([0, 1], [0, 1])
    assert 'size' in checks_found(pt.check(fig), 'error')


def test_thin_lines():
    fig, ax = clean_figure()
    ax.lines[0].set_linewidth(0.1)
    assert 'line_width' in checks_found(pt.check(fig))


def test_low_contrast_text():
    fig, ax = clean_figure()
    ax.text(0.05, 0.05, 'faint', transform=ax.transAxes, color='#dddddd')
    assert 'contrast' in checks_found(pt.check(fig))


def test_red_green_colour_blind_pair():
    fig, ax = clean_figure()
    ax.lines[0].set_color('#d62728')
    ax.lines[1].set_color('#2ca02c')
    msgs = [i.message for i in pt.check(fig) if i.check == 'colors']
    assert any('protanopia' in m or 'deuteranopia' in m for m in msgs), msgs


def test_okabe_ito_passes_colour_check():
    assert pt.colors.check_palette(pt.OKABE_ITO[:7], normal_min=10, cvd_min=6) == []


def test_rainbow_colormap():
    fig, ax = pt.figure('single')
    im = ax.imshow(np.random.default_rng(0).random((5, 5)), cmap='jet')
    assert 'colormap' in checks_found(pt.check(fig))


def test_variable_name_label_and_missing_legend():
    fig, ax = pt.figure('single')
    ax.plot([0, 1], [0, 1], label='a')
    ax.plot([0, 1], [1, 0], label='b')
    ax.set_xlabel('mean_auc_score')
    report = pt.check(fig)
    assert any('variable name' in i.message for i in report)
    assert any('no legend' in i.message for i in report)


def test_highlight_and_report_text():
    fig, ax = clean_figure()
    ax.text(1.02, 0.5, 'off the edge text', transform=ax.transAxes, in_layout=False)
    report = pt.check(fig)
    report.highlight()
    assert any(a.get_gid() == 'plottino-highlight' for a in fig.findobj())
    assert '[1]' in str(report)
    pt.clear_highlights(fig)
    assert not any(a.get_gid() == 'plottino-highlight' for a in fig.findobj())
    with pytest.raises(pt.FigureCheckError):
        report.raise_for_errors()


def test_latex_widths():
    j = pt.latex('article', fontsize=10)
    assert j.width(r'\textwidth') == pytest.approx(345 / 72.27)
    assert j.width(r'0.5\textwidth') == pytest.approx(345 / 72.27 / 2)
    assert j.width('0.5 linewidth') == pytest.approx(345 / 72.27 / 2)
    assert j.font_size == 8
    assert pt.latex('6.5in').width('textwidth') == pytest.approx(6.5)
    assert pt.latex(469.75).width('textwidth') == pytest.approx(6.5, rel=1e-3)
    with pytest.raises(ValueError):
        j.width('0.5 double')


def test_latex_figure_and_save(tmp_path, capsys):
    pt.use_latex('article', seaborn=False)
    fig, ax = pt.figure(r'0.5\textwidth', aspect=0.8)
    assert fig.get_size_inches()[0] == pytest.approx(345 / 72.27 / 2)
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel('x (a.u.)'), ax.set_ylabel('y (a.u.)')
    report = pt.save(fig, tmp_path / 'fig')
    assert (tmp_path / 'fig.pdf').exists() and (tmp_path / 'fig.png').exists()
    assert report.ok
    assert r'\includegraphics[width=0.5\textwidth]{fig}' in capsys.readouterr().out


def test_strict_save_refuses(tmp_path):
    fig, ax = clean_figure()
    ax.set_xlabel('Time (s)', fontsize=3)
    with pytest.raises(pt.FigureCheckError):
        pt.save(fig, tmp_path / 'bad.pdf', strict=True)
    assert not (tmp_path / 'bad.pdf').exists()


def test_overlay_written(tmp_path):
    fig, ax = clean_figure()
    ax.text(1.02, 0.5, 'off the edge text', transform=ax.transAxes, in_layout=False)
    pt.save(fig, tmp_path / 'f.pdf', quiet=True)
    assert (tmp_path / 'f.check.png').exists()


def test_seaborn_plot_checks():
    sns = pytest.importorskip('seaborn')
    pt.use('nature')
    fig, ax = pt.figure('single')
    rng = np.random.default_rng(1)
    sns.scatterplot(x=rng.normal(size=60), y=rng.normal(size=60), hue=np.repeat(['a', 'b', 'c'], 20), ax=ax)
    ax.set_xlabel('Score 1'), ax.set_ylabel('Score 2')
    report = pt.check(fig)
    assert 'text_clipped' not in checks_found(report)


def test_title_with_blank_line_for_subtitle():
    fig, ax = clean_figure()
    ax.get_legend().remove()
    ax.set_title('A message title\n', fontweight='bold')
    ax.text(0, 1.0, 'subtitle (n = 10)', transform=ax.transAxes, va='bottom')
    assert 'text_overlap' not in checks_found(pt.check(fig))


def test_tight_canvas_keeps_outside_text_but_changes_width():
    fig, ax = clean_figure()
    fig.set_layout_engine('none')
    ax.text(1.02, 0.5, 'a note beyond the axes', transform=ax.transAxes)
    assert 'text_clipped' in checks_found(pt.check(fig))
    report = pt.check(fig, tight=True)
    assert 'text_clipped' not in checks_found(report)
    assert any(i.check == 'size' and 'tight' in i.message for i in report)


def test_contrast_grouped_with_suggestion():
    fig, ax = clean_figure()
    for k in range(3):
        ax.text(0.1 + 0.3 * k, 0.05, f'n{k}', transform=ax.transAxes, color='#bbbbbb')
    msgs = [i.message for i in pt.check(fig) if i.check == 'contrast']
    assert len(msgs) == 1 and msgs[0].startswith('3 text(s)') and 'or darker reaches 3:1' in msgs[0]


def test_categorical_axis_needs_no_label():
    fig, ax = pt.figure('single')
    ax.barh(['GNN', 'RolX', 'Degree'], [0.8, 0.6, 0.55])
    ax.set_xlabel('Rank AUC')
    assert not any(i.check == 'labels' for i in pt.check(fig))


def test_label_lines_stay_inside_axes():
    fig, ax = pt.figure('double', aspect=0.38)
    x = np.linspace(0, 1, 50)
    for rate, name in [(3, 'Baseline'), (2, 'Model A'), (0.8, 'Ours')]:
        ax.plot(x, np.exp(-rate * x), label=name)
    pt.label_lines(ax)
    ax.set(xlabel='Threshold', ylabel='Recall')
    report = pt.check(fig)
    assert 'text_over_data' not in checks_found(report) and 'text_overlap' not in checks_found(report), report


def test_science_family_presets():
    sci, adv = pp_journal('science'), pp_journal('Science Advances')
    assert adv.width('single') == pytest.approx(3.5417, abs=1e-3)    # 21p3
    assert adv.width('double') == pytest.approx(7.25)                # 43p6
    assert adv.width('onehalf') == pytest.approx(5.6667, abs=1e-3)   # 34p
    for j in (sci, adv):
        assert (j.font_size, j.min_font, j.min_linewidth, j.panel_label_size, j.min_marker) == (8, 6, 0.28, 9, 5)


def pp_journal(name):
    return pt.journals.get(name)


def test_small_markers():
    pt.use('sciadv', seaborn=False)
    fig, ax = pt.figure('single')
    ax.scatter([0, 1, 2], [0, 1, 0], s=9)          # 3 pt across
    ax.plot([0, 1, 2], [1, 0, 1], marker='o', markersize=6)
    ax.set(xlabel='x (m)', ylabel='y (m)')
    msgs = [i.message for i in pt.check(fig) if i.check == 'marker_size']
    assert len(msgs) == 1 and '3 pt' in msgs[0]


def test_science_rules_title_and_minor_ticks():
    pt.use('sciadv', seaborn=False)
    fig, ax = pt.figure('single')
    ax.plot([1, 10, 100], [1, 2, 3])
    ax.set_xscale('log')                            # log axes get minor ticks
    ax.set(xlabel='Dose (mg)', ylabel='Response (a.u.)')
    fig.suptitle('Response rises with dose')
    msgs = [i.message for i in pt.check(fig) if i.check == 'journal_rules']
    assert any('minor ticks' in m for m in msgs) and any('figure title' in m for m in msgs)
    ax.minorticks_off()
    fig._suptitle.remove(); fig._suptitle = None
    assert 'journal_rules' not in checks_found(pt.check(fig))
    # other journals have no such rules
    fig2, ax2 = clean_figure()
    fig2.suptitle('A title')
    assert 'journal_rules' not in checks_found(pt.check(fig2, journal='pnas', width='double'))


def test_panel_labels_use_journal_size():
    pt.use('science', seaborn=False)
    fig, axes = pt.figure('double', ncols=2)
    for ax in axes:
        ax.plot([0, 1], [0, 1]); ax.set(xlabel='x (m)', ylabel='y (m)')
    labels = pt.panel_labels(axes)
    assert [t.get_fontsize() for t in labels] == [9, 9]
    assert not any(i.check == 'font_size' for i in pt.check(fig))   # 9 pt allowed for panel letters only
    labels[0].set_fontsize(12)
    assert any('panel letter' in i.message for i in pt.check(fig))


def test_nature_rules():
    pt.use('nature', seaborn=False)
    fig, ax = pt.figure('single')
    assert not ax.xaxis.get_major_ticks()[0].gridline.get_visible()   # the Nature style has no grid
    ax.plot([0, 1, 2], [0, 1, 4], label='model')
    ax.set(xlabel='Time (s)', ylabel='Distance')                       # y has no unit
    ax.text(1, 3, 'model', color='#0072B2')                            # coloured text
    pt.panel_labels([ax], ['A'], x=-0.2)                               # Nature uses lowercase
    msgs = ' | '.join(i.message for i in pt.check(fig) if i.check == 'journal_rules')
    assert 'no coloured text' in msgs and 'without units' in msgs and 'lowercase' in msgs
    assert 'gridlines' not in msgs and 'axis lines' not in msgs
    ax.grid(True)
    ax.spines['left'].set_visible(False)
    msgs = ' | '.join(i.message for i in pt.check(fig) if i.check == 'journal_rules')
    assert 'no background gridlines' in msgs and 'axis lines and tick marks' in msgs


def test_red_green_and_blue_yellow_rules():
    def fig_with(colors, journal):
        pt.use(journal, seaborn=False)
        fig, ax = pt.figure('single')
        for k, c in enumerate(colors):
            ax.plot([0, 1], [k, k + 1], color=c)
        ax.set(xlabel='Time (s)', ylabel='Signal (V)')
        return [i.message for i in pt.check(fig) if i.check == 'journal_rules']
    assert any('red and green' in m for m in fig_with(['#d62728', '#2ca02c'], 'cell'))
    assert not any('red and green' in m for m in fig_with(['#eb6834', '#0072B2'], 'cell'))   # orange is not red
    assert any('dark blue and yellow' in m for m in fig_with(['#0072B2', '#F0E442'], 'science'))
    assert not any('dark blue and yellow' in m for m in fig_with(['#0072B2', '#F0E442'], 'cell'))


def test_cell_preset():
    j = pt.journals.get('cell')
    assert j.width('single') == pytest.approx(85 / 25.4) and j.width('third') == pytest.approx(55 / 25.4)
    assert j.fonts == ('Arial',) and 'no_figure_title' in j.rules and j.min_linewidth == 0.5
