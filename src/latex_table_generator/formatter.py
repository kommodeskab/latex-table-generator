"""Formatting utilities for numbers, uncertainties, and LaTeX styling."""

from __future__ import annotations

import math
from typing import Any


def _parse_format_spec(format_spec: str | None) -> tuple[str | None, list[str]]:
    """Parse format specifier into (number_spec, styles).

    Examples:
        ".2f" -> (".2f", [])
        "bold" -> (None, ["bold"])
        ".2f|bold" -> (".2f", ["bold"])
        ".3f:italic:bold" -> (".3f", ["italic", "bold"])
    """
    if not format_spec:
        return None, []

    parts = [
        p.strip()
        for p in format_spec.replace(":", "|").replace(",", "|").split("|")
        if p.strip()
    ]
    num_spec = None
    styles: list[str] = []

    style_keywords = {"bold", "textbf", "italic", "textit", "underline", "math", "code"}

    for part in parts:
        if part.lower() in style_keywords:
            styles.append(part.lower())
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
                styles.append(part.lower())

    return num_spec, styles


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
) -> str:
    """Format a single numeric or string value for LaTeX table display.

    Parameters
    ----------
    val : Any
        The value to format.
    decimals : int, optional
        Default number of decimals if format_spec does not specify precision.
    format_spec : str, optional
        Format specifier string (e.g. '.2f', '.1%', 'bold', '.3f|bold').
    extra_styles : list of str, optional
        Additional style modifiers to apply (e.g. ['bold', 'underline']).
    color : str, optional
        Text color name or hex code.
    cell_color : str, optional
        Background color for the entire cell.

    Returns
    -------
    str
        Formatted string.
    """
    if val is None:
        return apply_latex_styles(
            "-", styles=extra_styles, color=color, cell_color=cell_color
        )

    if isinstance(val, float) and math.isnan(val):
        return apply_latex_styles(
            "-", styles=extra_styles, color=color, cell_color=cell_color
        )

    num_spec, styles = _parse_format_spec(format_spec)
    if extra_styles:
        for st in extra_styles:
            if st not in styles:
                styles.append(st)

    # If it's a float or int, format numerically
    if isinstance(val, (int, float)):
        if num_spec:
            try:
                formatted = format(val, num_spec)
            except (ValueError, TypeError):
                formatted = str(val)
        elif decimals is not None:
            formatted = f"{float(val):.{decimals}f}"
        else:
            formatted = str(val)
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
) -> str:
    """Format a mean and standard deviation uncertainty pair.

    Parameters
    ----------
    mean_val : Any
        The central value (mean).
    std_val : Any
        The uncertainty value (standard deviation).
    decimals : int, optional
        Default number of decimals for both mean and std.
    format_spec : str, optional
        Format specifier string applied to numbers and style applied to result.
    pm_symbol : str, default r"\\ensuremath{\\pm}"
        LaTeX symbol to use for plus-minus sign.
    extra_styles : list of str, optional
        Additional style modifiers to apply (e.g. ['bold', 'underline']).
    color : str, optional
        Text color name or hex code.
    cell_color : str, optional
        Background color for the entire cell.

    Returns
    -------
    str
        Formatted string (e.g. '\\cellcolor{yellow!25} 0.85 \\ensuremath{\\pm} 0.02').
    """
    num_spec, styles = _parse_format_spec(format_spec)
    if extra_styles:
        for st in extra_styles:
            if st not in styles:
                styles.append(st)

    # Format mean and std with the numerical spec (without styles yet)
    mean_str = format_value(mean_val, decimals=decimals, format_spec=num_spec)
    std_str = format_value(std_val, decimals=decimals, format_spec=num_spec)

    combined = f"{mean_str} {pm_symbol} {std_str}"
    return apply_latex_styles(combined, styles, color=color, cell_color=cell_color)
