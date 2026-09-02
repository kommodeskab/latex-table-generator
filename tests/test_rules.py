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
    decimals: 3
    bold_highest: true
    underline_lowest: true
    color: "blue"
  lat_group:
    decimals: 1
    bold_lowest: true
    color: "#FF5733"
default:
  decimals: 2
"""
    config = RulesConfig.from_yaml(yaml_content)
    assert "acc_group" in config
    assert "lat_group" in config

    acc_rule = config.get_rule("acc_group")
    assert acc_rule.decimals == 3
    assert acc_rule.bold_highest is True
    assert acc_rule.underline_lowest is True
    assert acc_rule.color == "blue"

    lat_rule = config.get_rule("lat_group")
    assert lat_rule.decimals == 1
    assert lat_rule.bold_lowest is True
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
                    "decimals": 2,
                    "bold_highest": True,
                    "underline_lowest": True,
                },
                "latency": {
                    "decimals": 1,
                    "bold_lowest": True,
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

    # Model B has highest accuracy (0.8856) -> bold
    # Model A has lowest accuracy (0.7512) -> underline
    # Model A has lowest latency (12.4) -> bold
    assert (
        r"Model A & \underline{0.75 \ensuremath{\pm} 0.01} & \textbf{12.4} \\" in result
    )
    assert r"Model B & \textbf{0.89 \ensuremath{\pm} 0.01} & 24.8 \\" in result
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
                    "decimals": 3,
                    "bold_highest": True,
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
        r"Model B & \textcolor{ForestGreen}{\textbf{\textit{0.886}}} \\" in result
        or r"Model B & \textcolor{ForestGreen}{\textit{\textbf{0.886}}} \\" in result
    )
    assert "Model C & 0.812 \\\\" in result


def test_pipe_group_syntax(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {"decimals": 2, "bold_highest": True},
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
    assert r"Model B & \textbf{0.89 \ensuremath{\pm} 0.01} \\" in result


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
    decimals: 2
    bold_highest: true
  lat:
    decimals: 1
    bold_lowest: true
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
        r"M1 & 0.70 \ensuremath{\pm} 0.01 & \textcolor{darkgray}{\textbf{10.0}} \\"
        in result
    )
    assert (
        r"M2 & \textbf{0.90 \ensuremath{\pm} 0.02} & \textcolor{darkgray}{30.0} \\"
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


def test_cell_color_highest_and_lowest(sample_metrics):
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "decimals": 2,
                    "cell_color_highest": "green!20",
                    "cell_color_lowest": "red!15",
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

    # Model B is highest (0.8856) -> green!20
    # Model A is lowest (0.7512) -> red!15
    # Model C is middle (0.8123) -> no cellcolor
    assert r"Model A & \cellcolor{red!15} 0.75 \ensuremath{\pm} 0.01 \\" in result
    assert r"Model B & \cellcolor{green!20} 0.89 \ensuremath{\pm} 0.01 \\" in result
    assert r"Model C & 0.81 \ensuremath{\pm} 0.01 \\" in result
