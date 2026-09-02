"""Formatting utilities for numbers, uncertainties, and LaTeX styling."""

from __future__ import annotations

import math
from typing import Any


SI_PREFIXES = [
    (1e24, "Y"),
    (1e21, "Z"),
    (1e18, "E"),
    (1e15, "P"),
    (1e12, "T"),
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1e0, ""),
    (1e-3, "m"),
    (1e-6, r"\ensuremath{\mu}"),
    (1e-9, "n"),
    (1e-12, "p"),
    (1e-15, "f"),
    (1e-18, "a"),
]

BINARY_PREFIXES = [
    (1024**8, "Yi"),
    (1024**7, "Zi"),
    (1024**6, "Ei"),
    (1024**5, "Pi"),
    (1024**4, "Ti"),
    (1024**3, "Gi"),
    (1024**2, "Mi"),
    (1024**1, "Ki"),
    (1, ""),
]


def get_si_prefix_scaling(val: float, mode: str | bool = "si") -> tuple[float, str]:
    """Determine the scaling factor and prefix string for a numeric value.

    Parameters
    ----------
    val : float
        Numeric value to scale.
    mode : str or bool, default "si"
        "si" / "metric" / True for standard SI (base 1000), "binary" / "iec" for base 1024.

    Returns
    -------
    tuple of (factor, prefix_str)
        e.g. for val = 175_000_000, returns (1e6, "M").
    """
    if val is None or math.isnan(val) or math.isinf(val) or val == 0:
        return 1.0, ""

    abs_val = abs(float(val))
    mode_str = str(mode).lower().strip()

    if mode_str in ("binary", "iec", "bin"):
        for factor, prefix in BINARY_PREFIXES:
            if abs_val >= factor * 0.9999999:
                return float(factor), prefix
        return 1.0, ""
    else:
        # Standard SI prefixes
        if abs_val >= 1.0:
            for factor, prefix in SI_PREFIXES:
                if factor >= 1.0 and abs_val >= factor * 0.9999999:
                    return factor, prefix
            return 1.0, ""
        else:
            for factor, prefix in SI_PREFIXES:
                if abs_val >= factor * 0.9999999:
                    return factor, prefix
            return SI_PREFIXES[-1]


def _parse_format_spec(
    format_spec: str | None,
) -> tuple[str | None, list[str], str | bool | None, float | None, str | None]:
    """Parse format specifier into (number_spec, styles, auto_scale, scale, unit).

    Examples:
        ".2f" -> (".2f", [], None, None, None)
        "bold" -> (None, ["bold"], None, None, None)
        ".2f|bold" -> (".2f", ["bold"], None, None, None)
        ".1f|si|unit=B" -> (".1f", [], "si", None, "B")
        "scale=100|unit=%" -> (None, [], None, 100.0, "%")
    """
    if not format_spec:
        return None, [], None, None, None

    parts = [
        p.strip()
        for p in format_spec.replace(":", "|").replace(",", "|").split("|")
        if p.strip()
    ]
    num_spec = None
    styles: list[str] = []
    auto_scale: str | bool | None = None
    scale: float | None = None
    unit: str | None = None

    style_keywords = {"bold", "textbf", "italic", "textit", "underline", "math", "code"}

    for part in parts:
        p_lower = part.lower()
        if p_lower in style_keywords:
            styles.append(p_lower)
        elif p_lower in ("si", "si_prefix", "auto_scale", "autoscale"):
            auto_scale = "si"
        elif p_lower in ("binary", "iec", "bin"):
            auto_scale = "binary"
        elif p_lower.startswith("scale=") or p_lower.startswith("factor="):
            try:
                scale = float(part.split("=", 1)[1].strip())
            except ValueError:
                pass
        elif p_lower.startswith("unit=") or p_lower.startswith("suffix="):
            unit = part.split("=", 1)[1].strip()
        elif part.startswith(".") or any(c in part for c in "fFedgG%"):
            num_spec = part
        elif part in ("d", "i", "s"):
            num_spec = part
        else:
            # Check if it's a valid python format spec
            try:
                format(1.0, part)
                num_spec = part
            except ValueError:
                styles.append(p_lower)

    return num_spec, styles, auto_scale, scale, unit


def apply_latex_color(text: str, color: str | None) -> str:
    """Apply LaTeX color command using xcolor package syntax."""
    if not color:
        return text
    color_clean = str(color).strip()
    if not color_clean:
        return text

    if color_clean.startswith("#"):
        hex_code = color_clean[1:].strip()
        return f"\\textcolor[HTML]{{{hex_code}}}{{{text}}}"
    elif color_clean.lower().startswith("html:"):
        hex_code = color_clean[5:].strip()
        return f"\\textcolor[HTML]{{{hex_code}}}{{{text}}}"
    elif color_clean.lower().startswith("rgb:"):
        rgb_code = color_clean[4:].strip()
        return f"\\textcolor[RGB]{{{rgb_code}}}{{{text}}}"
    else:
        return f"\\textcolor{{{color_clean}}}{{{text}}}"


def apply_latex_cell_color(text: str, cell_color: str | None) -> str:
    """Apply LaTeX cellcolor command for full-cell background coloring."""
    if not cell_color:
        return text
    cc_clean = str(cell_color).strip()
    if not cc_clean:
        return text

    if cc_clean.startswith("#"):
        hex_code = cc_clean[1:].strip()
        return f"\\cellcolor[HTML]{{{hex_code}}} {text}"
    elif cc_clean.lower().startswith("html:"):
        hex_code = cc_clean[5:].strip()
        return f"\\cellcolor[HTML]{{{hex_code}}} {text}"
    elif cc_clean.lower().startswith("rgb:"):
        rgb_code = cc_clean[4:].strip()
        return f"\\cellcolor[RGB]{{{rgb_code}}} {text}"
    else:
        return f"\\cellcolor{{{cc_clean}}} {text}"


def apply_latex_styles(
    text: str,
    styles: list[str] | None = None,
    color: str | None = None,
    cell_color: str | None = None,
) -> str:
    """Apply LaTeX style wrappers (e.g. \\textbf, \\textit, \\underline, \\textcolor, \\cellcolor) to text."""
    result = text
    if styles:
        for style in styles:
            s = style.lower().strip()
            if s in ("bold", "textbf"):
                result = f"\\textbf{{{result}}}"
            elif s in ("italic", "textit"):
                result = f"\\textit{{{result}}}"
            elif s in ("underline",):
                result = f"\\underline{{{result}}}"
            elif s in ("math",):
                result = f"${result}$"
            elif s in ("code",):
                result = f"\\texttt{{{result}}}"

    if color:
        result = apply_latex_color(result, color)

    if cell_color:
        result = apply_latex_cell_color(result, cell_color)

    return result


def format_value(
    val: Any,
    decimals: int | None = None,
    format_spec: str | None = None,
    extra_styles: list[str] | None = None,
    color: str | None = None,
    cell_color: str | None = None,
    auto_scale: str | bool | None = None,
    scale: float | None = None,
    unit: str | None = None,
) -> str:
    """Format a single numeric or string value for LaTeX table display with auto-scaling."""
    if val is None:
        return apply_latex_styles(
            "-", styles=extra_styles, color=color, cell_color=cell_color
        )

    if isinstance(val, float) and math.isnan(val):
        return apply_latex_styles(
            "-", styles=extra_styles, color=color, cell_color=cell_color
        )

    num_spec, styles, spec_auto_scale, spec_scale, spec_unit = _parse_format_spec(
        format_spec
    )
    if extra_styles:
        for st in extra_styles:
            if st not in styles:
                styles.append(st)

    effective_auto_scale = (
        spec_auto_scale if spec_auto_scale is not None else auto_scale
    )
    effective_scale = spec_scale if spec_scale is not None else scale
    effective_unit = spec_unit if spec_unit is not None else unit

    # If it's a float or int, format numerically
    if isinstance(val, (int, float)):
        unit_str = ""
        scaled_val: float = float(val)

        if effective_auto_scale:
            factor, prefix = get_si_prefix_scaling(val, mode=effective_auto_scale)
            scaled_val = float(val) / factor
            unit_str = f"{prefix}{effective_unit or ''}"
        elif effective_scale is not None:
            scaled_val = float(val) * effective_scale
            unit_str = effective_unit or ""
        elif effective_unit:
            unit_str = effective_unit

        if num_spec:
            try:
                formatted_num = format(scaled_val, num_spec)
            except (ValueError, TypeError):
                formatted_num = str(scaled_val)
        elif decimals is not None:
            formatted_num = f"{scaled_val:.{decimals}f}"
        else:
            formatted_num = str(scaled_val)

        formatted = f"{formatted_num}{unit_str}"
    else:
        # String or other type
        formatted = str(val)

    return apply_latex_styles(formatted, styles, color=color, cell_color=cell_color)


def format_uncertainty(
    mean_val: Any,
    std_val: Any,
    decimals: int | None = None,
    format_spec: str | None = None,
    pm_symbol: str = r"\ensuremath{\pm}",
    extra_styles: list[str] | None = None,
    color: str | None = None,
    cell_color: str | None = None,
    auto_scale: str | bool | None = None,
    scale: float | None = None,
    unit: str | None = None,
) -> str:
    """Format a mean and standard deviation uncertainty pair with SI prefix scaling."""
    num_spec, styles, spec_auto_scale, spec_scale, spec_unit = _parse_format_spec(
        format_spec
    )
    if extra_styles:
        for st in extra_styles:
            if st not in styles:
                styles.append(st)

    effective_auto_scale = (
        spec_auto_scale if spec_auto_scale is not None else auto_scale
    )
    effective_scale = spec_scale if spec_scale is not None else scale
    effective_unit = spec_unit if spec_unit is not None else unit

    unit_str = ""
    if isinstance(mean_val, (int, float)) and isinstance(std_val, (int, float)):
        scaled_mean: float = float(mean_val)
        scaled_std: float = float(std_val)

        if effective_auto_scale:
            factor, prefix = get_si_prefix_scaling(mean_val, mode=effective_auto_scale)
            scaled_mean = float(mean_val) / factor
            scaled_std = float(std_val) / factor
            unit_str = f"{prefix}{effective_unit or ''}"
        elif effective_scale is not None:
            scaled_mean = float(mean_val) * effective_scale
            scaled_std = float(std_val) * effective_scale
            unit_str = effective_unit or ""
        elif effective_unit:
            unit_str = effective_unit

        mean_str = format_value(scaled_mean, decimals=decimals, format_spec=num_spec)
        std_str = format_value(scaled_std, decimals=decimals, format_spec=num_spec)
    else:
        mean_str = format_value(mean_val, decimals=decimals, format_spec=num_spec)
        std_str = format_value(std_val, decimals=decimals, format_spec=num_spec)

    combined = f"{mean_str} {pm_symbol} {std_str}{unit_str}"
    return apply_latex_styles(combined, styles, color=color, cell_color=cell_color)
