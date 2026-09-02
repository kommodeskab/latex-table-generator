"""Tests for auto-scaling, SI prefixes, binary prefixes, and unit scaling."""

from latex_table_generator.formatter import (
    format_uncertainty,
    format_value,
    get_si_prefix_scaling,
)
from latex_table_generator.metrics import MetricsStore
from latex_table_generator.rules import RulesConfig
from latex_table_generator.template import TemplateRenderer


def test_get_si_prefix_scaling():
    # Mega
    factor, prefix = get_si_prefix_scaling(175_000_000)
    assert factor == 1e6
    assert prefix == "M"

    # Giga
    factor, prefix = get_si_prefix_scaling(4.5e9)
    assert factor == 1e9
    assert prefix == "G"

    # Kilo
    factor, prefix = get_si_prefix_scaling(25_400)
    assert factor == 1e3
    assert prefix == "k"

    # No prefix (1.0 to 999.9)
    factor, prefix = get_si_prefix_scaling(45.2)
    assert factor == 1.0
    assert prefix == ""

    # Milli
    factor, prefix = get_si_prefix_scaling(0.0035)
    assert factor == 1e-3
    assert prefix == "m"

    # Micro
    factor, prefix = get_si_prefix_scaling(0.000012)
    assert factor == 1e-6
    assert prefix == r"\ensuremath{\mu}"

    # Binary IEC
    factor, prefix = get_si_prefix_scaling(16 * 1024 * 1024 * 1024, mode="binary")
    assert factor == 1024**3
    assert prefix == "Gi"


def test_format_value_si_scaling():
    # Value in millions with unit 'B'
    res = format_value(175_000_000, decimals=1, auto_scale="si", unit="B")
    assert res == "175.0MB"

    # Value in micro-seconds
    res = format_value(0.000045, decimals=1, auto_scale="si", unit="s")
    assert res == r"45.0\ensuremath{\mu}s"

    # Zero value
    res = format_value(0, decimals=1, auto_scale="si", unit="B")
    assert res == "0.0B"


def test_format_uncertainty_si_scaling():
    # Mean 125M, std 1.5M -> both scaled by 1e6
    res = format_uncertainty(
        125_000_000,
        1_500_000,
        decimals=1,
        auto_scale="si",
        unit="B",
    )
    assert res == r"125.0 \ensuremath{\pm} 1.5MB"


def test_format_scale_multiplier():
    # Multiplier 100 for percentages
    res = format_value(0.8812, decimals=2, scale=100, unit="%")
    assert res == "88.12%"

    # Uncertainty with scale multiplier
    res = format_uncertainty(0.8812, 0.0054, decimals=2, scale=100, unit="%")
    assert res == r"88.12 \ensuremath{\pm} 0.54%"


def test_group_rules_with_auto_scale_and_units():
    metrics = MetricsStore(
        {
            "res18": {"params": 11_700_000, "flops": 1_820_000_000, "time_s": 0.000012},
            "swin": {"params": 88_000_000, "flops": 15_400_000_000, "time_s": 0.000052},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "p_group": {
                    "higher_is_better": False,
                    "si_prefix": True,
                    "decimals": 1,
                    "unit": " params",
                    "bold": 1,
                },
                "f_group": {
                    "si_prefix": True,
                    "decimals": 2,
                    "unit": "FLOPs",
                },
                "t_group": {
                    "si_prefix": True,
                    "decimals": 1,
                    "unit": "s",
                },
            }
        }
    )

    template = (
        "ResNet-18 & [p_group]{res18.params} & [f_group]{res18.flops} & [t_group]{res18.time_s} \\\\\n"
        "Swin & [p_group]{swin.params} & [f_group]{swin.flops} & [t_group]{swin.time_s} \\\\"
    )

    renderer = TemplateRenderer(metrics, rules=rules)
    result = renderer.render(template)

    assert (
        r"ResNet-18 & \textbf{11.7M params} & 1.82GFLOPs & 12.0\ensuremath{\mu}s \\"
        in result
    )
    assert r"Swin & 88.0M params & 15.40GFLOPs & 52.0\ensuremath{\mu}s \\" in result


def test_format_spec_inline_si_and_scale():
    metrics = MetricsStore(
        {
            "m1": {"large_num": 250_000_000, "frac": 0.7645},
        }
    )

    template = "M1 & {m1.large_num:.1f|si|unit=B} & {m1.frac:.2f|scale=100|unit=%} \\\\"

    renderer = TemplateRenderer(metrics)
    result = renderer.render(template)

    assert "M1 & 250.0MB & 76.45% \\\\" in result
