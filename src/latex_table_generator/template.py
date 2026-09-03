"""Template engine for processing and rendering LaTeX tables with metric placeholders and group rules."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from latex_table_generator.formatter import (
    _parse_format_spec,
    apply_latex_cell_color,
    apply_latex_color,
    apply_latex_styles,
    format_uncertainty,
    format_value,
    get_si_prefix_scaling,
)
from latex_table_generator.metrics import MetricsStore, load_metrics
from latex_table_generator.rules import GroupRule, RulesConfig, load_rules

# Regex to match uncertainty operators: +- , +/- , \pm , ±
UNCERTAINTY_PATTERN = re.compile(r"\s*(?:\+\-|\+\/\-|\\pm|±)\s*")

# Regex to match group prefixes like [group1, group2] or [@group1]
PREFIX_GROUP_REGEX = re.compile(r"^\[(?P<groups>[a-zA-Z0-9_\- ,@]+)\]")

# Match placeholder with optional prefix [groups]
TAGGED_PLACEHOLDER_REGEX = re.compile(
    r"(?<!\\)(?:\[(?P<prefix_groups>[a-zA-Z0-9_\- ,@]+)\]\s*)?\{(?P<inner>[^{}]+)\}"
)

# Match plain text with group prefix [groups]text
TAGGED_TEXT_REGEX = re.compile(
    r"(?<!\\)\[(?P<prefix_groups>[a-zA-Z0-9_\- ,@]+)\]\s*(?P<text>[^&\\\{\}\n]+)"
)


def _is_metric_target(target: str) -> bool:
    """Determine if a string looks like a row.column metric identifier."""
    target = target.strip()
    if not target or target.startswith("\\"):
        return False
    if "." not in target:
        return False
    # Check if it's something like "0.5\textwidth" or "1.5cm"
    if re.match(r"^\d*\.?\d+\s*(?:\\?[a-zA-Z]+)?$", target):
        return False
    # Must have non-empty parts before and after at least one dot
    parts = target.split(".")
    if any(not p.strip() for p in parts):
        return False
    return True


def _parse_target_parts(
    target_str: str,
    metrics: MetricsStore | None = None,
) -> tuple[str, str]:
    """Parse target_str into (row_name, col_name), using MetricsStore for smart resolution if available."""
    target_str = target_str.strip()

    # Handle quoted parts e.g. "Model 1.0".acc or 'Model 1.0'.acc
    quoted_match = re.match(
        r"""^(?:['"](?P<q_row>[^'"]+)['"]\.(?P<q_col>.+)|(?P<row>.+)\.['"](?P<q2_col>[^'"]+)['"])$""",
        target_str,
    )
    if quoted_match:
        groups = quoted_match.groupdict()
        row = groups.get("q_row") or groups.get("row") or ""
        col = groups.get("q_col") or groups.get("q2_col") or ""
        return row.strip(), col.strip()

    if metrics is not None:
        # Try all split positions on dot to match existing metric in store
        dot_indices = [i for i, c in enumerate(target_str) if c == "."]
        for idx in dot_indices:
            cand_row = target_str[:idx].strip()
            cand_col = target_str[idx + 1 :].strip()
            if metrics.has_metric(cand_row, cand_col):
                return cand_row, cand_col

        # Try if candidate row exists in metrics
        for idx in dot_indices:
            cand_row = target_str[:idx].strip()
            cand_col = target_str[idx + 1 :].strip()
            if metrics.has_row(cand_row):
                return cand_row, cand_col

        # Try if candidate col exists in metrics
        for idx in dot_indices:
            cand_row = target_str[:idx].strip()
            cand_col = target_str[idx + 1 :].strip()
            if metrics.has_column(cand_col):
                return cand_row, cand_col

    # Fallback: split on first dot
    parts = target_str.split(".", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return target_str.strip(), ""


def _extract_group_names(raw_groups: str | None) -> list[str]:
    """Clean and parse comma/pipe separated group names."""
    if not raw_groups:
        return []
    result: list[str] = []
    for g in raw_groups.replace("|", ",").split(","):
        clean_g = g.strip().lstrip("@").strip()
        if clean_g.lower().startswith("group:"):
            clean_g = clean_g[6:].strip()
        elif clean_g.lower().startswith("group="):
            clean_g = clean_g[6:].strip()
        elif clean_g.lower().startswith("groups="):
            clean_g = clean_g[7:].strip()
        if clean_g and clean_g not in result:
            result.append(clean_g)
    return result


@dataclass
class _ItemMatch:
    match_id: int
    span: tuple[int, int]
    raw_text: str
    groups: list[str]
    is_uncertainty: bool
    is_plain_text: bool
    val1: Any = None
    val2: Any = None
    numeric_val: float | None = None
    format_spec: str | None = None
    plain_content: str | None = None
    assigned_styles: list[str] = field(default_factory=list)
    assigned_cell_color: str | None = None
    assigned_color: str | None = None
    table_idx: int = 0
    col_idx: int = -1
    align_prefix: str = ""
    align_suffix: str = ""


class TemplateRenderer:
    """Renders LaTeX table templates by substituting metric placeholders and applying group rules."""

    def __init__(
        self,
        metrics: MetricsStore | Any,
        rules: RulesConfig | Mapping[str, Any] | str | Path | None = None,
        decimals: int | None = None,
        pm_symbol: str = r"\ensuremath{\pm}",
        align_columns: bool = False,
        align_numbers: bool = True,
        strict: bool = False,
    ) -> None:
        self.metrics = load_metrics(metrics)
        self.rules: RulesConfig = load_rules(rules)
        self.decimals = decimals
        self.pm_symbol = pm_symbol
        self.align_columns = align_columns
        self.align_numbers = align_numbers
        self.strict = strict

    def _parse_inner_expression(
        self,
        inner: str,
        prefix_groups: list[str],
    ) -> tuple[bool, Any, Any, float | None, str | None, list[str]] | None:
        """Parse inner placeholder content into (is_uncertainty, val1, val2, numeric_val, format_spec, groups)."""
        inner_trimmed = inner.strip()
        groups = list(prefix_groups)

        # Check for groups or format specifier inside placeholder e.g. {row.col | group1, group2} or {row.col : .2f}
        format_spec: str | None = None
        main_expr = inner_trimmed

        # Check for pipe syntax: expr | group_or_spec
        if "|" in inner_trimmed:
            parts = inner_trimmed.split("|")
            main_expr = parts[0].strip()
            for extra in parts[1:]:
                extra_clean = extra.strip()
                extra_lower = extra_clean.lower()
                # Check if it's a group name or format spec
                if (
                    extra_clean.startswith(".")
                    or extra_lower
                    in (
                        "bold",
                        "textbf",
                        "italic",
                        "textit",
                        "underline",
                        "math",
                        "code",
                        "si",
                        "si_prefix",
                        "auto_scale",
                        "binary",
                        "iec",
                    )
                    or extra_lower.startswith("scale=")
                    or extra_lower.startswith("unit=")
                    or extra_lower.startswith("factor=")
                ):
                    format_spec = (
                        extra_clean
                        if not format_spec
                        else f"{format_spec}|{extra_clean}"
                    )
                else:
                    for g in _extract_group_names(extra_clean):
                        if g not in groups:
                            groups.append(g)

        # Check for colon syntax in main_expr: expr : spec_or_group
        if ":" in main_expr:
            parts = main_expr.rsplit(":", 1)
            candidate_expr = parts[0].strip()
            candidate_spec = parts[1].strip()
            cand_lower = candidate_spec.lower()
            if cand_lower.startswith("group=") or cand_lower.startswith("groups="):
                main_expr = candidate_expr
                for g in _extract_group_names(candidate_spec):
                    if g not in groups:
                        groups.append(g)
            elif (
                candidate_spec.startswith(".")
                or cand_lower
                in (
                    "bold",
                    "textbf",
                    "italic",
                    "textit",
                    "underline",
                    "math",
                    "code",
                    "si",
                    "si_prefix",
                    "auto_scale",
                    "binary",
                    "iec",
                )
                or cand_lower.startswith("scale=")
                or cand_lower.startswith("unit=")
                or cand_lower.startswith("factor=")
            ):
                main_expr = candidate_expr
                format_spec = (
                    candidate_spec
                    if not format_spec
                    else f"{candidate_spec}|{format_spec}"
                )
            elif self.rules.has_group(candidate_spec):
                main_expr = candidate_expr
                if candidate_spec not in groups:
                    groups.append(candidate_spec)

        # Check for uncertainty expression: target1 (+-|\pm|+/-|±) target2
        uncertainty_match = UNCERTAINTY_PATTERN.search(main_expr)
        if uncertainty_match:
            left_target = main_expr[: uncertainty_match.start()].strip()
            right_target = main_expr[uncertainty_match.end() :].strip()

            if _is_metric_target(left_target) and _is_metric_target(right_target):
                r1, c1 = _parse_target_parts(left_target, self.metrics)
                r2, c2 = _parse_target_parts(right_target, self.metrics)
                mean_val = self.metrics.get(r1, c1)
                std_val = self.metrics.get(r2, c2)
                numeric_val = (
                    float(mean_val)
                    if isinstance(mean_val, (int, float)) and not math.isnan(mean_val)
                    else None
                )
                return True, mean_val, std_val, numeric_val, format_spec, groups

        # Check for single metric expression: row.col
        if _is_metric_target(main_expr):
            r, c = _parse_target_parts(main_expr, self.metrics)
            is_recognized = (
                self.metrics.has_metric(r, c)
                or self.metrics.has_row(r)
                or self.metrics.has_column(c)
                or self.strict
            )

            if is_recognized:
                val = self.metrics.get(r, c)
                numeric_val = (
                    float(val)
                    if isinstance(val, (int, float)) and not math.isnan(val)
                    else None
                )
                return False, val, None, numeric_val, format_spec, groups

        return None

    def _collect_items(self, template_str: str) -> list[_ItemMatch]:
        """Scan template string and collect all metric placeholders and tagged cells."""
        items: list[_ItemMatch] = []
        match_id = 0

        # Pass 1: Tagged placeholders: [groups]{...} or {...}
        for m in TAGGED_PLACEHOLDER_REGEX.finditer(template_str):
            prefix_raw = m.group("prefix_groups")
            prefix_groups = _extract_group_names(prefix_raw)
            inner = m.group("inner")

            parsed = self._parse_inner_expression(inner, prefix_groups)
            if parsed is not None:
                is_unc, v1, v2, num_v, fmt_spec, item_groups = parsed
                start, end = m.span()
                line_start = template_str.rfind("\n", 0, start)
                line_start = 0 if line_start == -1 else line_start + 1
                line_end = template_str.find("\n", end)
                line_end = len(template_str) if line_end == -1 else line_end
                line = template_str[line_start:line_end]

                if "&" in line:
                    col_idx = template_str[line_start:start].count("&")
                else:
                    col_idx = -1

                table_idx = template_str[:start].count(r"\begin{tabular}")

                items.append(
                    _ItemMatch(
                        match_id=match_id,
                        span=m.span(),
                        raw_text=m.group(0),
                        groups=item_groups,
                        is_uncertainty=is_unc,
                        is_plain_text=False,
                        val1=v1,
                        val2=v2,
                        numeric_val=num_v,
                        format_spec=fmt_spec,
                        table_idx=table_idx,
                        col_idx=col_idx,
                    )
                )
                match_id += 1

        return items

    def _get_item_rounded_value(self, it: _ItemMatch, rule: GroupRule) -> float:
        """Compute the displayed rounded numerical value for an item within a group."""
        if it.numeric_val is None:
            return 0.0

        # 1. Determine effective decimals
        decimals = self.decimals
        if self.rules.default_rule.decimals is not None:
            decimals = self.rules.default_rule.decimals
        if rule.decimals is not None:
            decimals = rule.decimals
        for g in it.groups:
            g_rule = self.rules.get_rule(g)
            if g_rule.decimals is not None:
                decimals = g_rule.decimals
                break

        num_spec, _, spec_auto, spec_scale, _ = _parse_format_spec(it.format_spec)
        if num_spec and num_spec.startswith("."):
            try:
                spec_dec = int("".join(c for c in num_spec[1:] if c.isdigit()))
                decimals = spec_dec
            except ValueError:
                pass

        auto_scale = spec_auto if spec_auto is not None else rule.auto_scale
        scale = spec_scale if spec_scale is not None else rule.scale

        val = float(it.numeric_val)
        if auto_scale:
            factor, _ = get_si_prefix_scaling(val, mode=auto_scale)
            scaled_val = val / factor
        elif scale is not None:
            scaled_val = val * scale
        else:
            scaled_val = val

        if decimals is not None:
            return round(scaled_val, decimals)
        return scaled_val

    def _evaluate_group_extremums(self, items: list[_ItemMatch]) -> None:
        """Calculate ranked highlights (bold, underline, colors) for each group based on rounded values."""
        group_items_map: dict[str, list[_ItemMatch]] = {}
        for item in items:
            for g in item.groups:
                if g not in group_items_map:
                    group_items_map[g] = []
                group_items_map[g].append(item)

        for group_name, g_items in group_items_map.items():
            rule = self.rules.get_rule(group_name)
            valid_numeric_items = [it for it in g_items if it.numeric_val is not None]
            if not valid_numeric_items:
                continue

            # Compute rounded displayed value for each item
            item_rounded_map = {
                it.match_id: self._get_item_rounded_value(it, rule)
                for it in valid_numeric_items
            }

            # Sort unique rounded values by rank: reverse=True if higher_is_better else reverse=False
            unique_vals = sorted(
                list(set(item_rounded_map[it.match_id] for it in valid_numeric_items)),
                reverse=rule.higher_is_better,
            )

            for rank_idx, rank_val in enumerate(unique_vals, start=1):
                # Apply style to all items that tie/score the same rounded value
                matching_items = [
                    it
                    for it in valid_numeric_items
                    if math.isclose(
                        item_rounded_map[it.match_id], rank_val, rel_tol=1e-9
                    )
                ]

                for it in matching_items:
                    # 1. Bold rank
                    if rank_idx in rule.bold:
                        if "bold" not in it.assigned_styles:
                            it.assigned_styles.append("bold")

                    # 2. Underline rank
                    if rank_idx in rule.underline:
                        if "underline" not in it.assigned_styles:
                            it.assigned_styles.append("underline")

                    # 3. Italic rank
                    if rank_idx in rule.italic:
                        if "italic" not in it.assigned_styles:
                            it.assigned_styles.append("italic")

                    # 4. Cell background color for rank
                    if rank_idx in rule.cell_color_ranks:
                        it.assigned_cell_color = rule.cell_color_ranks[rank_idx]

                    # 5. Text color for rank
                    if rank_idx in rule.color_ranks:
                        it.assigned_color = rule.color_ranks[rank_idx]

    def _get_item_config(
        self, item: _ItemMatch
    ) -> tuple[int | None, str | bool | None, float | None, str | None]:
        """Determine decimals, auto_scale, scale, and unit for an item."""
        decimals = self.decimals
        for g in item.groups:
            rule = self.rules.get_rule(g)
            if rule.decimals is not None:
                decimals = rule.decimals
                break
        else:
            if self.rules.default_rule.decimals is not None:
                decimals = self.rules.default_rule.decimals

        auto_scale: str | bool | None = None
        scale: float | None = None
        unit: str | None = None
        for g in item.groups:
            rule = self.rules.get_rule(g)
            if auto_scale is None and rule.auto_scale is not None:
                auto_scale = rule.auto_scale
            if scale is None and rule.scale is not None:
                scale = rule.scale
            if unit is None and rule.unit is not None:
                unit = rule.unit

        if auto_scale is None and self.rules.default_rule.auto_scale is not None:
            auto_scale = self.rules.default_rule.auto_scale
        if scale is None and self.rules.default_rule.scale is not None:
            scale = self.rules.default_rule.scale
        if unit is None and self.rules.default_rule.unit is not None:
            unit = self.rules.default_rule.unit

        return decimals, auto_scale, scale, unit

    def _evaluate_column_alignment(self, items: list[_ItemMatch]) -> None:
        """Calculate phantom prefixes and suffixes so that values in each column align cleanly."""
        if not self.align_numbers:
            return

        if self.rules.default_rule.align_numbers is False:
            return

        from collections import defaultdict

        col_groups: dict[Any, list[_ItemMatch]] = defaultdict(list)
        for it in items:
            if it.numeric_val is None and not it.is_uncertainty:
                continue

            opt_out = False
            for g in it.groups:
                if self.rules.get_rule(g).align_numbers is False:
                    opt_out = True
                    break
            if opt_out:
                continue

            if it.col_idx >= 0:
                key = (it.table_idx, it.col_idx)
            elif it.groups:
                key = ("group", it.groups[0])
            else:
                continue

            col_groups[key].append(it)

        for key, col_items in col_groups.items():
            if len(col_items) < 2:
                continue

            item_infos = []
            for it in col_items:
                val = it.val1 if it.is_uncertainty else it.numeric_val
                if val is None or not isinstance(val, (int, float)) or math.isnan(val):
                    continue

                decimals, auto_scale, scale, unit = self._get_item_config(it)
                (
                    num_spec,
                    _,
                    spec_auto_scale,
                    spec_scale,
                    spec_unit,
                ) = _parse_format_spec(it.format_spec)
                eff_auto_scale = (
                    spec_auto_scale if spec_auto_scale is not None else auto_scale
                )
                eff_scale = spec_scale if spec_scale is not None else scale

                if eff_auto_scale:
                    factor, _ = get_si_prefix_scaling(val, mode=eff_auto_scale)
                    scaled_val = float(val) / factor
                elif eff_scale is not None:
                    scaled_val = float(val) * eff_scale
                else:
                    scaled_val = float(val)

                if num_spec:
                    try:
                        formatted_str = format(scaled_val, num_spec)
                    except Exception:
                        formatted_str = str(scaled_val)
                elif decimals is not None:
                    formatted_str = f"{scaled_val:.{decimals}f}"
                else:
                    formatted_str = str(scaled_val)

                is_neg = formatted_str.startswith("-")
                clean_num = formatted_str.lstrip("-")
                if "." in clean_num:
                    int_part, dec_part = clean_num.split(".", 1)
                    has_dot = True
                else:
                    int_part, dec_part = clean_num, ""
                    has_dot = False

                item_infos.append(
                    {
                        "item": it,
                        "is_neg": is_neg,
                        "int_digits": len(int_part),
                        "dec_digits": len(dec_part),
                        "has_dot": has_dot,
                    }
                )

            if len(item_infos) < 2:
                continue

            has_negative = any(info["is_neg"] for info in item_infos)
            max_int_digits = max(info["int_digits"] for info in item_infos)
            max_dec_digits = max(info["dec_digits"] for info in item_infos)
            any_has_dot = any(info["has_dot"] for info in item_infos)

            for info in item_infos:
                it = info["item"]
                int_pad = max_int_digits - info["int_digits"]
                dec_pad = max_dec_digits - info["dec_digits"]

                # Prefix alignment
                if info["is_neg"]:
                    if int_pad > 0:
                        it.align_prefix = r"\hphantom{" + ("0" * int_pad) + "}"
                    else:
                        it.align_prefix = ""
                else:
                    pad_chars = ("-" if has_negative else "") + ("0" * int_pad)
                    if pad_chars:
                        it.align_prefix = r"\hphantom{" + pad_chars + "}"
                    else:
                        it.align_prefix = ""

                # Suffix alignment
                if dec_pad > 0:
                    dot_pad = (
                        r"\hphantom{.}" if (any_has_dot and not info["has_dot"]) else ""
                    )
                    it.align_suffix = dot_pad + r"\hphantom{" + ("0" * dec_pad) + "}"
                else:
                    it.align_suffix = ""

    def _render_item(self, item: _ItemMatch) -> str:
        """Render a single parsed item into its LaTeX formatted string."""
        decimals, auto_scale, scale, unit = self._get_item_config(item)

        # 2. Determine text color: item assigned rank color first, then group static color, then default
        color: str | None = item.assigned_color
        if not color:
            for g in item.groups:
                rule = self.rules.get_rule(g)
                if rule.color:
                    color = rule.color
                    break
            else:
                if self.rules.default_rule.color:
                    color = self.rules.default_rule.color

        # 3. Determine cell background color: item assigned rank cell color first, then static group cell_color
        cell_color: str | None = item.assigned_cell_color
        if not cell_color:
            for g in item.groups:
                rule = self.rules.get_rule(g)
                if rule.cell_color:
                    cell_color = rule.cell_color
                    break
            else:
                if self.rules.default_rule.cell_color:
                    cell_color = self.rules.default_rule.cell_color

        # 4. Combine styles: static group styles + extremum assigned styles
        styles: list[str] = list(item.assigned_styles)
        for g in item.groups:
            rule = self.rules.get_rule(g)
            for st in rule.styles:
                if st not in styles:
                    styles.append(st)

        # Check if number alignment is active and should preserve natural font width
        opt_out_align = not self.align_numbers
        if not opt_out_align:
            if self.rules.default_rule.align_numbers is False:
                opt_out_align = True
            else:
                for g in item.groups:
                    if self.rules.get_rule(g).align_numbers is False:
                        opt_out_align = True
                        break

        font_styles = [s for s in styles if s in ("bold", "textbf", "italic", "textit")]
        has_font_style = bool(font_styles)

        # 5. Format string
        if (
            not opt_out_align
            and has_font_style
            and (item.is_uncertainty or not item.is_plain_text)
        ):
            non_font_styles = [s for s in styles if s not in font_styles]

            if item.is_uncertainty:
                mean_text = format_value(
                    val=item.val1,
                    decimals=decimals,
                    format_spec=item.format_spec,
                    extra_styles=None,
                    color=None,
                    cell_color=None,
                    auto_scale=auto_scale,
                    scale=scale,
                    unit=None,
                )
                std_text = format_value(
                    val=item.val2,
                    decimals=decimals,
                    format_spec=item.format_spec,
                    extra_styles=None,
                    color=None,
                    cell_color=None,
                    auto_scale=auto_scale,
                    scale=scale,
                    unit=None,
                )
                styled_mean = apply_latex_styles(mean_text, styles=font_styles)
                styled_pm = apply_latex_styles(self.pm_symbol, styles=font_styles)
                styled_std = apply_latex_styles(std_text, styles=font_styles)

                content = (
                    f"\\phantom{{{mean_text}}}\\llap{{{styled_mean}}} "
                    f"\\rlap{{{styled_pm}}}\\phantom{{{self.pm_symbol}}} "
                    f"\\rlap{{{styled_std}}}\\phantom{{{std_text}}}"
                )
                if unit:
                    content = f"{content}{unit}"
            else:
                raw_text = format_value(
                    val=item.val1,
                    decimals=decimals,
                    format_spec=item.format_spec,
                    extra_styles=None,
                    color=None,
                    cell_color=None,
                    auto_scale=auto_scale,
                    scale=scale,
                    unit=unit,
                )

                if "." in raw_text:
                    dot_idx = raw_text.find(".")
                    left = raw_text[:dot_idx]
                    right = raw_text[dot_idx:]
                    styled_left = apply_latex_styles(left, styles=font_styles)
                    styled_right = apply_latex_styles(right, styles=font_styles)
                    content = (
                        f"\\phantom{{{left}}}\\llap{{{styled_left}}}"
                        f"\\rlap{{{styled_right}}}\\phantom{{{right}}}"
                    )
                else:
                    styled_left = apply_latex_styles(raw_text, styles=font_styles)
                    content = f"\\phantom{{{raw_text}}}\\llap{{{styled_left}}}"

            if non_font_styles:
                content = apply_latex_styles(content, styles=non_font_styles)
            if color:
                content = apply_latex_color(content, color)
        elif item.is_uncertainty:
            content = format_uncertainty(
                mean_val=item.val1,
                std_val=item.val2,
                decimals=decimals,
                format_spec=item.format_spec,
                pm_symbol=self.pm_symbol,
                extra_styles=styles,
                color=color,
                cell_color=None,
                auto_scale=auto_scale,
                scale=scale,
                unit=unit,
            )
        elif not item.is_plain_text:
            content = format_value(
                val=item.val1,
                decimals=decimals,
                format_spec=item.format_spec,
                extra_styles=styles,
                color=color,
                cell_color=None,
                auto_scale=auto_scale,
                scale=scale,
                unit=unit,
            )
        else:
            content = apply_latex_styles(
                item.plain_content or "",
                styles=styles,
                color=color,
                cell_color=None,
            )

        if item.align_prefix:
            content = f"{item.align_prefix}{content}"

        if item.align_suffix:
            if unit and content.endswith(unit):
                content = content[: -len(unit)] + item.align_suffix + unit
            else:
                content = f"{content}{item.align_suffix}"

        if cell_color:
            content = apply_latex_cell_color(content, cell_color)

        return content

    def render(self, template_str: str) -> str:
        """Render a template string into a LaTeX table applying metric values and group rules."""
        items = self._collect_items(template_str)

        # Calculate extremums (highest/lowest) per group
        self._evaluate_group_extremums(items)

        # Calculate column number alignment (phantom minus & digits)
        self._evaluate_column_alignment(items)

        # Replace items from right to left to preserve offsets
        rendered = template_str
        for item in sorted(items, key=lambda it: it.span[0], reverse=True):
            formatted_text = self._render_item(item)
            start, end = item.span
            rendered = rendered[:start] + formatted_text + rendered[end:]

        # Handle nested braces like \textbf{{row.col}} if any remain
        if "{" in rendered and "." in rendered:
            remaining_items = self._collect_items(rendered)
            if remaining_items:
                self._evaluate_group_extremums(remaining_items)
                self._evaluate_column_alignment(remaining_items)
                for item in sorted(
                    remaining_items, key=lambda it: it.span[0], reverse=True
                ):
                    formatted_text = self._render_item(item)
                    start, end = item.span
                    rendered = rendered[:start] + formatted_text + rendered[end:]

        if self.align_columns:
            rendered = align_latex_table(rendered)

        return rendered

    def render_file(
        self,
        template_path: str | Path,
        output_path: str | Path | None = None,
        encoding: str = "utf-8",
    ) -> str:
        """Read template from file, render it, and optionally write to output_path."""
        template_path_obj = Path(template_path)
        if not template_path_obj.is_file():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        template_str = template_path_obj.read_text(encoding=encoding)
        result = self.render(template_str)

        if output_path is not None:
            out_path_obj = Path(output_path)
            out_path_obj.parent.mkdir(parents=True, exist_ok=True)
            out_path_obj.write_text(result, encoding=encoding)

        return result


def align_latex_table(latex_str: str) -> str:
    """Align '&' and '\\\\' columns across rows in a LaTeX table for clean formatting."""
    lines = latex_str.splitlines()

    parsed_lines = []
    max_cols = 0
    col_widths: list[int] = []

    for line in lines:
        stripped = line.strip()
        # Skip pure comments or environment tags
        if (
            not stripped
            or stripped.startswith("%")
            or stripped.startswith("\\begin")
            or stripped.startswith("\\end")
            or (stripped.startswith("\\") and "&" not in stripped)
        ):
            parsed_lines.append({"type": "raw", "content": line})
            continue

        if "&" in line:
            # Check for trailing comment
            comment = ""
            row_content = line
            if "%" in line:
                parts = line.split("%", 1)
                row_content = parts[0]
                comment = "%" + parts[1]

            # Check for trailing \\ or \hline
            terminator = ""
            if "\\\\" in row_content:
                parts = row_content.rsplit("\\\\", 1)
                row_content = parts[0]
                terminator = "\\\\" + parts[1]

            cells = [c.strip() for c in row_content.split("&")]
            max_cols = max(max_cols, len(cells))

            parsed_lines.append(
                {
                    "type": "row",
                    "cells": cells,
                    "terminator": terminator.strip(),
                    "comment": comment,
                    "indent": len(line) - len(line.lstrip()),
                }
            )
        else:
            parsed_lines.append({"type": "raw", "content": line})

    # Calculate max width for each column
    col_widths = [0] * max_cols
    for item in parsed_lines:
        if item["type"] == "row":
            for i, cell in enumerate(item["cells"]):
                col_widths[i] = max(col_widths[i], len(cell))

    # Rebuild lines
    output_lines = []
    for item in parsed_lines:
        if item["type"] == "raw":
            output_lines.append(item["content"])
        elif item["type"] == "row":
            indent_str = " " * item["indent"]
            padded_cells = [
                cell.ljust(col_widths[i]) if i < len(col_widths) - 1 else cell
                for i, cell in enumerate(item["cells"])
            ]
            row_str = f"{indent_str}" + " & ".join(padded_cells)
            if item["terminator"]:
                row_str += f" {item['terminator']}"
            if item["comment"]:
                row_str += f" {item['comment']}"
            output_lines.append(row_str)

    # Preserve trailing newline if original had one
    result = "\n".join(output_lines)
    if latex_str.endswith("\n"):
        result += "\n"
    return result
