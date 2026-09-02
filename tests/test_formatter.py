"""Tests for formatter utilities."""

from latex_table_generator.formatter import (
    apply_latex_styles,
    format_uncertainty,
    format_value,
)


def test_format_value_default_and_decimals():
    assert format_value(0.8523, decimals=2) == "0.85"
    assert format_value(0.8523, decimals=3) == "0.852"
    assert format_value(0.8, decimals=2) == "0.80"
    assert format_value(10, decimals=2) == "10.00"
    assert format_value(0.8523, decimals=None) == "0.8523"
    assert format_value(None) == "-"
    assert format_value(float("nan")) == "-"


def test_format_value_with_spec():
    assert format_value(0.8523, format_spec=".1%") == "85.2%"
    assert format_value(1234.56, format_spec=".2e") == "1.23e+03"
    assert format_value(0.85, format_spec="bold") == r"\textbf{0.85}"
    assert format_value(0.8523, format_spec=".2f|bold") == r"\textbf{0.85}"
    assert format_value(0.85, format_spec="italic") == r"\textit{0.85}"
    assert format_value(0.85, format_spec="underline") == r"\underline{0.85}"


def test_format_uncertainty():
    # Basic uncertainty (default \ensuremath{\pm})
    assert (
        format_uncertainty(0.8523, 0.0189, decimals=2) == r"0.85 \ensuremath{\pm} 0.02"
    )
    assert (
        format_uncertainty(0.8523, 0.0189, decimals=3)
        == r"0.852 \ensuremath{\pm} 0.019"
    )

    # Explicit \pm and $\pm$
    assert (
        format_uncertainty(0.8523, 0.0189, decimals=2, pm_symbol=r"\pm")
        == r"0.85 \pm 0.02"
    )
    assert (
        format_uncertainty(0.85, 0.02, decimals=2, pm_symbol=r"$\pm$")
        == r"0.85 $\pm$ 0.02"
    )

    # Styling
    assert (
        format_uncertainty(0.8523, 0.0189, decimals=2, format_spec="bold")
        == r"\textbf{0.85 \ensuremath{\pm} 0.02}"
    )
    assert (
        format_uncertainty(0.8523, 0.0189, decimals=2, format_spec=".3f|bold")
        == r"\textbf{0.852 \ensuremath{\pm} 0.019}"
    )


def test_apply_latex_styles():
    assert apply_latex_styles("text", ["bold"]) == r"\textbf{text}"
    assert apply_latex_styles("text", ["italic"]) == r"\textit{text}"
    assert apply_latex_styles("text", ["underline"]) == r"\underline{text}"
    assert apply_latex_styles("text", ["math"]) == r"$text$"
