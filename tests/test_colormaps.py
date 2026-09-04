"""Tests for color gradient, colormap interpolation, and heatmap rendering."""

import pytest
from latex_table_generator.colormaps import (
    get_colormap_hex,
    parse_color_to_rgb,
)
from latex_table_generator.metrics import MetricsStore
from latex_table_generator.rules import GroupRule, RulesConfig
from latex_table_generator.template import TemplateRenderer


def test_parse_color_to_rgb():
    assert parse_color_to_rgb("white") == (255, 255, 255)
    assert parse_color_to_rgb("black") == (0, 0, 0)
    assert parse_color_to_rgb("#ff0000") == (255, 0, 0)
    assert parse_color_to_rgb("#00f") == (0, 0, 255)
    assert parse_color_to_rgb("rgb: 10, 20, 30") == (10, 20, 30)

    with pytest.raises(ValueError, match="Unable to parse color"):
        parse_color_to_rgb("not_a_color_xyz")


def test_colormap_builtin_interpolation():
    c0, dark0 = get_colormap_hex("Blues", 0.0)
    c1, dark1 = get_colormap_hex("Blues", 1.0)
    assert c0 == "#F7FBFF"
    assert not dark0
    assert c1 == "#08519C"
    assert dark1

    # Reversed
    c_rev0, _ = get_colormap_hex("Blues_r", 0.0)
    assert c_rev0 == c1


def test_colormap_custom_list():
    hex_mid, _ = get_colormap_hex(["white", "black"], 0.5)
    # Midpoint between 255 and 0 is 128 (#808080)
    assert hex_mid == "#808080"


def test_colormap_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown colormap"):
        get_colormap_hex("nonexistent_colormap", 0.5)


def test_color_gradient_requires_colormap_validation():
    # Enabling color_gradient without colormap must raise ValueError
    with pytest.raises(ValueError, match="no colormap was specified"):
        GroupRule.from_dict("acc", {"color_gradient": True})

    with pytest.raises(ValueError, match="no colormap was specified"):
        GroupRule.from_dict("acc", {"gradient": True})


def test_color_gradient_cell_rendering():
    metrics = MetricsStore(
        {
            "M1": {"acc": 0.0},
            "M2": {"acc": 0.5},
            "M3": {"acc": 1.0},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "acc": {
                    "color_gradient": True,
                    "colormap": "Blues",
                    "decimals": 1,
                }
            }
        }
    )

    template = (
        "M1 & [acc]{M1.acc} \\\\\nM2 & [acc]{M2.acc} \\\\\nM3 & [acc]{M3.acc} \\\\"
    )
    rendered = TemplateRenderer(metrics, rules=rules).render(template)

    # Lowest (0.0) -> #F7FBFF
    assert r"\cellcolor[HTML]{F7FBFF}" in rendered
    # Highest (1.0) -> #08519C (dark -> contrast text white)
    assert r"\cellcolor[HTML]{08519C}" in rendered
    assert r"\textcolor{white}" in rendered


def test_color_gradient_custom_vmin_vmax():
    metrics = MetricsStore(
        {
            "M1": {"score": 50},
            "M2": {"score": 100},
        }
    )

    # vmin=0, vmax=100 -> score 50 is at t=0.5
    rules = RulesConfig.from_dict(
        {
            "groups": {
                "score_grp": {
                    "color_gradient": True,
                    "colormap": ["#000000", "#FFFFFF"],
                    "vmin": 0,
                    "vmax": 100,
                }
            }
        }
    )

    template = "M1 & [score_grp]{M1.score} \\\\\nM2 & [score_grp]{M2.score} \\\\"
    rendered = TemplateRenderer(metrics, rules=rules).render(template)

    # At 50, t=0.5 -> #808080
    assert r"\cellcolor[HTML]{808080}" in rendered
    # At 100, t=1.0 -> #FFFFFF
    assert r"\cellcolor[HTML]{FFFFFF}" in rendered


def test_color_gradient_target_text():
    metrics = MetricsStore(
        {
            "M1": {"val": 10},
            "M2": {"val": 20},
        }
    )

    rules = RulesConfig.from_dict(
        {
            "groups": {
                "val_grp": {
                    "color_gradient": True,
                    "colormap": "coolwarm",
                    "gradient_target": "text",
                }
            }
        }
    )

    template = "M1 & [val_grp]{M1.val} \\\\\nM2 & [val_grp]{M2.val} \\\\"
    rendered = TemplateRenderer(metrics, rules=rules).render(template)

    assert r"\textcolor[HTML]{" in rendered
    assert r"\cellcolor" not in rendered
