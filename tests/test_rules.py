"""Tests for group rules, decimal formatting per group, extremum highlighting, and text colors."""

from pathlib import Path
import pytest
from latex_table_generator.generator import generate_latex_table
from latex_table_generator.metrics import MetricsStore
from latex_table_generator.rules import RulesConfig
from latex_table_generator.template import TemplateRenderer


@pytest.fixture
def sample_metrics():
    return MetricsStore(
        {
            "ModelA": {"acc_mean": 0.7512, "acc_std": 0.0123, "latency": 12.4},
            "ModelB": {"acc_mean": 0.8856, "acc_std": 0.0098, "latency": 24.8},
            "ModelC": {"acc_mean": 0.8123, "acc_std": 0.0067, "latency": 45.2},
        }
    )


def test_rules_config_from_yaml():
    yaml_content = """
groups:
  acc_group:
    higher_is_better: true
    decimals: 3
    bold: 1
    underline: 2
    color: "blue"
  lat_group:
    higher_is_better: false
    decimals: 1
    bold: 1
    color: "#FF5733"
default:
  decimals: 2
"""
    config = RulesConfig.from_yaml(yaml_content)
    assert "acc_group" in config
    assert "lat_group" in config

    acc_rule = config.get_rule("acc_group")
    assert acc_rule.decimals == 3
    assert acc_rule.bold == [1]
    assert acc_rule.underline == [2]
    assert acc_rule.color == "blue"

    lat_rule = config.get_rule("lat_group")
    assert lat_rule.decimals == 1
    assert lat_rule.higher_is_better is False
    assert lat_rule.bold == [1]
    assert lat_rule.color == "#FF5733"

    assert config.default_rule.decimals == 2


def test_group_decimals_different_per_group(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "g_acc": {"decimals": 3},
                "g_lat": {"decimals": 1},
            },
            "default": {"decimals": 2},
        }
    )

    template = (
        "Model A & [g_acc]{ModelA.acc_mean} & [g_lat]{ModelA.latency} \\\\\n"
        "Model B & [g_acc]{ModelB.acc_mean} & [g_lat]{ModelB.latency} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    assert "Model A & 0.751 & 12.4 \\\\" in result
    assert "Model B & 0.886 & 24.8 \\\\" in result


def test_highlight_highest_lowest_ignoring_uncertainty(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "accuracy": {
                    "higher_is_better": True,
                    "decimals": 2,
                    "bold": 1,
                    "underline": 3,
                },
                "latency": {
                    "higher_is_better": False,
                    "decimals": 1,
                    "bold": 1,
                },
            }
        }
    )

    template = (
        "Model A & [accuracy]{ModelA.acc_mean +- ModelA.acc_std} & [latency]{ModelA.latency} \\\\\n"
        "Model B & [accuracy]{ModelB.acc_mean +- ModelB.acc_std} & [latency]{ModelB.latency} \\\\\n"
        "Model C & [accuracy]{ModelC.acc_mean +- ModelC.acc_std} & [latency]{ModelC.latency} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    # Model B has highest accuracy (0.8856) -> bold (Rank 1)
    # Model A has lowest accuracy (0.7512) -> underline (Rank 3)
    # Model A has lowest latency (12.4) -> bold (Rank 1 when higher_is_better=False)
    assert (
        r"Model A & \underline{0.75 \ensuremath{\pm} 0.01} & \phantom{12}\llap{\textbf{12}}\rlap{\textbf{.4}}\phantom{.4} \\"
        in result
    )
    assert (
        r"Model B & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.89 \ensuremath{\pm} 0.01}}\phantom{.89 \ensuremath{\pm} 0.01} & 24.8 \\"
        in result
    )
    assert r"Model C & 0.81 \ensuremath{\pm} 0.01 & 45.2 \\" in result


def test_unique_text_color_per_group(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "g_blue": {"color": "blue"},
                "g_hex": {"color": "#00AA00"},
            }
        }
    )

    template = "Model A & [g_blue]{ModelA.acc_mean} & [g_hex]{ModelA.latency} \\\\"

    renderer = TemplateRenderer(sample_metrics, rules=rules, decimals=2)
    result = renderer.render(template)

    assert (
        r"Model A & \textcolor{blue}{0.75} & \textcolor[HTML]{00AA00}{12.40} \\"
        in result
    )


def test_multiple_groups_per_cell(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "col_acc": {
                    "higher_is_better": True,
                    "decimals": 3,
                    "bold": 1,
                },
                "best_model": {
                    "color": "ForestGreen",
                    "styles": ["italic"],
                },
            }
        }
    )

    # Model B belongs to col_acc AND best_model
    template = (
        "Model A & [col_acc]{ModelA.acc_mean} \\\\\n"
        "Model B & [col_acc, best_model]{ModelB.acc_mean} \\\\\n"
        "Model C & [col_acc]{ModelC.acc_mean} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    # Model B is highest in col_acc (gets bold, 3 decimals) AND in best_model (gets ForestGreen and italic)
    assert "Model A & 0.751 \\\\" in result
    assert (
        r"Model B & \textcolor{ForestGreen}{\phantom{0}\llap{\textbf{\textit{0}}}\rlap{\textbf{\textit{.886}}}\phantom{.886}} \\"
        in result
        or r"Model B & \textcolor{ForestGreen}{\phantom{0}\llap{\textit{\textbf{0}}}\rlap{\textit{\textbf{.886}}}\phantom{.886}} \\"
        in result
    )
    assert "Model C & 0.812 \\\\" in result


def test_pipe_group_syntax(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {"higher_is_better": True, "decimals": 2, "bold": 1},
            }
        }
    )

    template = (
        "Model A & {ModelA.acc_mean +- ModelA.acc_std | acc} \\\\\n"
        "Model B & {ModelB.acc_mean +- ModelB.acc_std | acc} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    assert r"Model A & 0.75 \ensuremath{\pm} 0.01 \\" in result
    assert (
        r"Model B & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.89 \ensuremath{\pm} 0.01}}\phantom{.89 \ensuremath{\pm} 0.01} \\"
        in result
    )


def test_end_to_end_rules_file(tmp_path: Path):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text(
        "model,acc_mean,acc_std,f1,lat\n"
        "M1,0.70,0.01,0.68,10.0\n"
        "M2,0.90,0.02,0.89,30.0\n",
        encoding="utf-8",
    )

    template_file = tmp_path / "template.txt"
    template_file.write_text(
        "\\begin{tabular}{lcc}\n"
        "Model & Accuracy & Latency \\\\\n"
        "\\hline\n"
        "M1 & [acc]{M1.acc_mean +- M1.acc_std} & [lat]{M1.lat} \\\\\n"
        "M2 & [acc]{M2.acc_mean +- M2.acc_std} & [lat]{M2.lat} \\\\\n"
        "\\end{tabular}\n",
        encoding="utf-8",
    )

    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        """
groups:
  acc:
    higher_is_better: true
    decimals: 2
    bold: 1
  lat:
    higher_is_better: false
    decimals: 1
    bold: 1
    color: "darkgray"
""",
        encoding="utf-8",
    )

    out_file = tmp_path / "table.tex"

    result = generate_latex_table(
        csv_path=csv_file,
        template_path=template_file,
        rules_path=rules_file,
        output_path=out_file,
    )

    assert (
        r"M1 & 0.70 \ensuremath{\pm} 0.01 & \textcolor{darkgray}{\phantom{10}\llap{\textbf{10}}\rlap{\textbf{.0}}\phantom{.0}} \\"
        in result
    )
    assert (
        r"M2 & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.90 \ensuremath{\pm} 0.02}}\phantom{.90 \ensuremath{\pm} 0.02} & \textcolor{darkgray}{30.0} \\"
        in result
    )
    assert out_file.exists()


def test_cell_background_color(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "g_bg": {"cell_color": "yellow!25"},
                "g_hex_bg": {"cell_color": "#E8F5E9"},
            }
        }
    )

    template = "Model A & [g_bg]{ModelA.acc_mean} & [g_hex_bg]{ModelA.latency} \\\\"
    renderer = TemplateRenderer(sample_metrics, rules=rules, decimals=2)
    result = renderer.render(template)

    assert (
        r"Model A & \cellcolor{yellow!25} 0.75 & \cellcolor[HTML]{E8F5E9} 12.40 \\"
        in result
    )


def test_cell_color_ranks(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "higher_is_better": True,
                    "decimals": 2,
                    "cell_color": {
                        1: "green!20",
                        3: "red!15",
                    },
                }
            }
        }
    )

    template = (
        "Model A & [acc]{ModelA.acc_mean +- ModelA.acc_std} \\\\\n"
        "Model B & [acc]{ModelB.acc_mean +- ModelB.acc_std} \\\\\n"
        "Model C & [acc]{ModelC.acc_mean +- ModelC.acc_std} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    # Model B is highest (0.8856) -> Rank 1 -> green!20
    # Model A is lowest (0.7512) -> Rank 3 -> red!15
    # Model C is middle (0.8123) -> Rank 2 -> no cellcolor
    assert r"Model A & \cellcolor{red!15} 0.75 \ensuremath{\pm} 0.01 \\" in result
    assert r"Model B & \cellcolor{green!20} 0.89 \ensuremath{\pm} 0.01 \\" in result
    assert r"Model C & 0.81 \ensuremath{\pm} 0.01 \\" in result


def test_rank_based_bold_and_higher_is_better(sample_metrics):
    # ModelA: acc=0.7512 (rank 3), lat=12.4 (rank 1 best)
    # ModelB: acc=0.8856 (rank 1 best), lat=24.8 (rank 2)
    # ModelC: acc=0.8123 (rank 2), lat=45.2 (rank 3)
    rules = RulesConfig.from_dict(
        {
            "groups": {
                # Accuracy: higher_is_better=True, 2nd highest should be bold
                "acc": {
                    "higher_is_better": True,
                    "bold": 2,
                    "decimals": 2,
                },
                # Latency: higher_is_better=False, lowest should be underlined
                "lat": {
                    "higher_is_better": False,
                    "underline": 1,
                    "decimals": 1,
                },
            }
        }
    )

    template = (
        "Model A & [acc]{ModelA.acc_mean} & [lat]{ModelA.latency} \\\\\n"
        "Model B & [acc]{ModelB.acc_mean} & [lat]{ModelB.latency} \\\\\n"
        "Model C & [acc]{ModelC.acc_mean} & [lat]{ModelC.latency} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    # Model C has 2nd highest accuracy (0.8123) -> bold
    # Model A has lowest latency (12.4) -> underline
    assert r"Model A & 0.75 & \underline{12.4} \\" in result
    assert r"Model B & 0.89 & 24.8 \\" in result
    assert (
        r"Model C & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.81}}\phantom{.81} & 45.2 \\"
        in result
    )


def test_rank_based_multiple_ranks_and_colors(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "higher_is_better": True,
                    "bold": 1,
                    "underline": 2,
                    "cell_color": {1: "green!20", 2: "yellow!15"},
                    "decimals": 2,
                }
            }
        }
    )

    template = (
        "Model A & [acc]{ModelA.acc_mean} \\\\\n"
        "Model B & [acc]{ModelB.acc_mean} \\\\\n"
        "Model C & [acc]{ModelC.acc_mean} \\\\"
    )

    renderer = TemplateRenderer(sample_metrics, rules=rules)
    result = renderer.render(template)

    # Model B is Rank 1 -> bold & cell_color green!20
    # Model C is Rank 2 -> underline & cell_color yellow!15
    assert r"Model A & 0.75 \\" in result
    assert (
        r"Model B & \cellcolor{green!20} \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.89}}\phantom{.89} \\"
        in result
    )
    assert r"Model C & \cellcolor{yellow!15} \underline{0.81} \\" in result


def test_rounded_value_ranking_ties():
    # Model A: 0.884 -> rounds to 0.88
    # Model B: 0.881 -> rounds to 0.88
    # Model C: 0.852 -> rounds to 0.85
    # Both Model A and Model B should tie for Rank 1 and both be bold!
    # Model C is Rank 2 and should be underlined!
    metrics = MetricsStore(
        {
            "ModelA": {"acc": 0.884, "err": 12.44},
            "ModelB": {"acc": 0.881, "err": 12.41},
            "ModelC": {"acc": 0.852, "err": 24.80},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "higher_is_better": True,
                    "bold": 1,
                    "underline": 2,
                    "decimals": 2,
                },
                "err": {
                    "higher_is_better": False,
                    "bold": 1,
                    "decimals": 1,
                },
            }
        }
    )

    template = (
        "Model A & [acc]{ModelA.acc} & [err]{ModelA.err} \\\\\n"
        "Model B & [acc]{ModelB.acc} & [err]{ModelB.err} \\\\\n"
        "Model C & [acc]{ModelC.acc} & [err]{ModelC.err} \\\\"
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    # Both Model A (0.88) and Model B (0.88) get bold
    # Model C (0.85) gets underline
    # In error (lower is better, 1 decimal): Model A (12.4) and Model B (12.4) both get bold!
    assert (
        r"Model A & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.88}}\phantom{.88} & \phantom{12}\llap{\textbf{12}}\rlap{\textbf{.4}}\phantom{.4} \\"
        in result
    )
    assert (
        r"Model B & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.88}}\phantom{.88} & \phantom{12}\llap{\textbf{12}}\rlap{\textbf{.4}}\phantom{.4} \\"
        in result
    )
    assert r"Model C & \underline{0.85} & 24.8 \\" in result


def test_rank_based_italic_styling():
    metrics = MetricsStore(
        {
            "M1": {"acc": 0.95, "loss": 0.10},
            "M2": {"acc": 0.90, "loss": 0.20},
            "M3": {"acc": 0.85, "loss": 0.30},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "higher_is_better": True,
                    "bold": 1,
                    "underline": 2,
                    "italic": 3,
                    "decimals": 2,
                },
                "loss": {
                    "higher_is_better": False,
                    "italic": 1,
                    "decimals": 2,
                },
            }
        }
    )

    template = (
        "M1 & [acc]{M1.acc} & [loss]{M1.loss} \\\\\n"
        "M2 & [acc]{M2.acc} & [loss]{M2.loss} \\\\\n"
        "M3 & [acc]{M3.acc} & [loss]{M3.loss} \\\\"
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    # acc: M1 (0.95) -> bold, M2 (0.90) -> underline, M3 (0.85) -> italic
    # loss: M1 (0.10, lowest) -> italic
    assert (
        r"M1 & \phantom{0}\llap{\textbf{0}}\rlap{\textbf{.95}}\phantom{.95} & \phantom{0}\llap{\textit{0}}\rlap{\textit{.10}}\phantom{.10} \\"
        in result
    )
    assert r"M2 & \underline{0.90} & 0.20 \\" in result
    assert (
        r"M3 & \phantom{0}\llap{\textit{0}}\rlap{\textit{.85}}\phantom{.85} & 0.30 \\"
        in result
    )


def test_align_column_numbers_with_minus_and_positives():
    metrics = MetricsStore(
        {
            "M1": {"loss": -18.65, "diff": -0.12},
            "M2": {"loss": 0.69, "diff": 1.45},
            "M3": {"loss": -2.14, "diff": -3.60},
        }
    )

    template = (
        "\\begin{tabular}{lcc}\n"
        "Model & Loss & Diff \\\\\n"
        "M1 & [loss]{M1.loss} & [diff]{M1.diff} \\\\\n"
        "M2 & [loss]{M2.loss} & [diff]{M2.diff} \\\\\n"
        "M3 & [loss]{M3.loss} & [diff]{M3.diff} \\\\\n"
        "\\end{tabular}"
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "loss": {"decimals": 2},
                "diff": {"decimals": 2},
            }
        }
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    # In diff: all have 1 integer digit. M2 is positive, so it gets \hphantom{-}
    # In loss: max integer digits = 2. M1 is -18.65 (2 digits).
    # M2 is 0.69 (1 digit, positive) -> gets \hphantom{-0}
    # M3 is -2.14 (1 digit, negative) -> gets \hphantom{0}
    assert r"M1 & -18.65 & -0.12 \\" in result
    assert r"M2 & \hphantom{-0}0.69 & \hphantom{-}1.45 \\" in result
    assert r"M3 & \hphantom{0}-2.14 & -3.60 \\" in result


def test_disable_align_numbers():
    metrics = MetricsStore(
        {
            "M1": {"loss": -18.65},
            "M2": {"loss": 0.69},
        }
    )

    template = "M1 & {M1.loss} \\\\\nM2 & {M2.loss} \\\\"

    # When align_numbers is False, no \hphantom padding is added
    renderer = TemplateRenderer(metrics, decimals=2, align_numbers=False)
    result = renderer.render(template)

    assert "M1 & -18.65 \\\\" in result
    assert "M2 & 0.69 \\\\" in result


def test_align_numbers_uncertainties_with_minus():
    metrics = MetricsStore(
        {
            "M1": {"acc_mean": -0.76, "acc_std": 0.01},
            "M2": {"acc_mean": 0.88, "acc_std": 0.01},
        }
    )

    template = (
        "\\begin{tabular}{lc}\n"
        "M1 & {M1.acc_mean +- M1.acc_std} \\\\\n"
        "M2 & {M2.acc_mean +- M2.acc_std} \\\\\n"
        "\\end{tabular}"
    )

    renderer = TemplateRenderer(metrics, decimals=2)
    result = renderer.render(template)

    assert r"M1 & -0.76 \ensuremath{\pm} 0.01 \\" in result
    assert r"M2 & \hphantom{-}0.88 \ensuremath{\pm} 0.01 \\" in result


def test_opt_out_align_numbers_via_group_rule():
    metrics = MetricsStore(
        {
            "M1": {"col_a": -1.2, "col_b": -5.0},
            "M2": {"col_a": 1.2, "col_b": 5.0},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "g_opt_out": {"align_numbers": False, "decimals": 1},
                "g_normal": {"decimals": 1},
            }
        }
    )

    template = (
        "\\begin{tabular}{lcc}\n"
        "M1 & [g_opt_out]{M1.col_a} & [g_normal]{M1.col_b} \\\\\n"
        "M2 & [g_opt_out]{M2.col_a} & [g_normal]{M2.col_b} \\\\\n"
        "\\end{tabular}"
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    # g_opt_out opted out: M2.col_a is 1.2 (no phantom)
    # g_normal opted in: M2.col_b is \hphantom{-}5.0
    assert r"M1 & -1.2 & -5.0 \\" in result
    assert r"M2 & 1.2 & \hphantom{-}5.0 \\" in result


def test_style_width_alignment_bold_italic_underline():
    """Verify that bold and italic styles preserve natural unstyled widths so column numbers don't shift."""
    metrics = MetricsStore(
        {
            "M1": {"snr_mean": 9.84, "snr_std": 1.23},
            "M2": {"snr_mean": -4.43, "snr_std": 2.31},
            "M3": {"snr_mean": 10.24, "snr_std": 0.76},
            "M4": {"snr_mean": -18.23, "snr_std": 3.46},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "snr": {
                    "higher_is_better": True,
                    "bold": 1,
                    "underline": 2,
                    "decimals": 2,
                }
            }
        }
    )

    template = (
        "\\begin{tabular}{c}\n"
        "M1 & [snr]{M1.snr_mean +- M1.snr_std} \\\\\n"
        "M2 & [snr]{M2.snr_mean +- M2.snr_std} \\\\\n"
        "M3 & [snr]{M3.snr_mean +- M3.snr_std} \\\\\n"
        "M4 & [snr]{M4.snr_mean +- M4.snr_std} \\\\\n"
        "\\end{tabular}"
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    # M1 (Rank 2) -> underline (does not change font metrics, so standard underline)
    assert r"M1 & \hphantom{-0}\underline{9.84 \ensuremath{\pm} 1.23} \\" in result
    # M2 -> normal negative with phantom zero
    assert r"M2 & \hphantom{0}-4.43 \ensuremath{\pm} 2.31 \\" in result
    # M3 (Rank 1) -> bold with zero-width overlay around dot and unstyled phantom widths
    assert (
        r"M3 & \hphantom{-}\phantom{10}\llap{\textbf{10}}\rlap{\textbf{.24 \ensuremath{\pm} 0.76}}\phantom{.24 \ensuremath{\pm} 0.76} \\"
        in result
    )
    # M4 -> normal negative
    assert r"M4 & -18.23 \ensuremath{\pm} 3.46 \\" in result
