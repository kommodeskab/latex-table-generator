"""Rules and Group configuration for LaTeX table styling and metric formatting."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
import yaml


@dataclass
class GroupRule:
    """Styling and formatting rules for a group of table cells."""

    name: str
    higher_is_better: bool = True
    bold: list[int] = field(default_factory=list)
    underline: list[int] = field(default_factory=list)
    color: str | None = None
    color_ranks: dict[int, str] = field(default_factory=dict)
    cell_color: str | None = None
    cell_color_ranks: dict[int, str] = field(default_factory=dict)
    decimals: int | None = None
    auto_scale: str | bool | None = None
    scale: float | None = None
    unit: str | None = None
    styles: list[str] = field(default_factory=list)
    custom_format: str | None = None

    # Backwards compatibility fields
    bold_highest: bool = False
    bold_lowest: bool = False
    underline_highest: bool = False
    underline_lowest: bool = False
    highlight_highest: list[str] = field(default_factory=list)
    highlight_lowest: list[str] = field(default_factory=list)
    highlight_second_highest: list[str] = field(default_factory=list)
    highlight_second_lowest: list[str] = field(default_factory=list)
    cell_color_highest: str | None = None
    cell_color_lowest: str | None = None
    cell_color_second_highest: str | None = None
    cell_color_second_lowest: str | None = None

    @classmethod
    def from_dict(cls, name: str, data: Mapping[str, Any] | None) -> GroupRule:
        if not data:
            return cls(name=name)

        # 1. higher_is_better: defaults to True
        higher_is_better_raw = data.get("higher_is_better")
        if higher_is_better_raw is None:
            higher_is_better = True
        else:
            higher_is_better = bool(higher_is_better_raw)

        # 2. Parse rank lists (supports integer like `bold: 1`, list like `bold: [1, 2]`, boolean `bold: true`)
        def _parse_rank_list(val: Any) -> list[int]:
            if val is None:
                return []
            if isinstance(val, bool):
                return [1] if val else []
            if isinstance(val, int):
                return [val]
            if isinstance(val, str):
                res: list[int] = []
                for p in val.replace(",", "|").split("|"):
                    p_str = p.strip()
                    if p_str.isdigit():
                        res.append(int(p_str))
                return res
            if isinstance(val, (list, tuple)):
                res = []
                for item in val:
                    if isinstance(item, int):
                        res.append(item)
                    elif isinstance(item, str) and item.strip().isdigit():
                        res.append(int(item.strip()))
                    elif isinstance(item, bool) and item:
                        res.append(1)
                return res
            return []

        bold_ranks = _parse_rank_list(data.get("bold"))
        underline_ranks = _parse_rank_list(data.get("underline"))

        # Legacy flags: bold_highest / bold_lowest / underline_highest / underline_lowest
        bold_highest = bool(data.get("bold_highest", False))
        bold_lowest = bool(data.get("bold_lowest", False))
        underline_highest = bool(data.get("underline_highest", False))
        underline_lowest = bool(data.get("underline_lowest", False))

        if bold_highest and 1 not in bold_ranks and higher_is_better:
            bold_ranks.append(1)
        if bold_lowest and 1 not in bold_ranks and not higher_is_better:
            bold_ranks.append(1)

        if underline_highest and 1 not in underline_ranks and higher_is_better:
            underline_ranks.append(1)
        if underline_lowest and 1 not in underline_ranks and not higher_is_better:
            underline_ranks.append(1)

        # 3. Parse text colors (static string or rank dict)
        color_ranks: dict[int, str] = {}
        raw_color = data.get("color")
        static_color: str | None = None
        if isinstance(raw_color, dict):
            for k, v in raw_color.items():
                if str(k).isdigit() and v:
                    color_ranks[int(k)] = str(v).strip()
        elif raw_color is not None:
            static_color = str(raw_color).strip()

        for k, v in data.items():
            k_lower = k.lower()
            if k_lower.startswith("color_") and k_lower[6:].isdigit() and v:
                color_ranks[int(k_lower[6:])] = str(v).strip()

        # 4. Parse cell background colors (static string or rank dict)
        cell_color_ranks: dict[int, str] = {}
        raw_cell_color = (
            data.get("cell_color")
            or data.get("bg_color")
            or data.get("background_color")
        )
        static_cell_color: str | None = None
        if isinstance(raw_cell_color, dict):
            for k, v in raw_cell_color.items():
                if str(k).isdigit() and v:
                    cell_color_ranks[int(k)] = str(v).strip()
        elif raw_cell_color is not None:
            static_cell_color = str(raw_cell_color).strip()

        for k, v in data.items():
            k_lower = k.lower()
            if (
                k_lower.startswith("cell_color_")
                or k_lower.startswith("bg_color_")
                or k_lower.startswith("bg_")
            ):
                suffix = k_lower.rsplit("_", 1)[1]
                if suffix.isdigit() and v:
                    cell_color_ranks[int(suffix)] = str(v).strip()

        # Legacy cell_color_highest / lowest / second_highest
        cell_color_highest = (
            data.get("cell_color_highest")
            or data.get("bg_color_highest")
            or data.get("bg_highest")
        )
        if cell_color_highest is not None:
            cell_color_highest = str(cell_color_highest).strip()
            if higher_is_better and 1 not in cell_color_ranks:
                cell_color_ranks[1] = cell_color_highest

        cell_color_lowest = (
            data.get("cell_color_lowest")
            or data.get("bg_color_lowest")
            or data.get("bg_lowest")
        )
        if cell_color_lowest is not None:
            cell_color_lowest = str(cell_color_lowest).strip()
            if not higher_is_better and 1 not in cell_color_ranks:
                cell_color_ranks[1] = cell_color_lowest

        cell_color_2nd_highest = data.get("cell_color_second_highest") or data.get(
            "bg_second_highest"
        )
        if cell_color_2nd_highest is not None:
            cell_color_2nd_highest = str(cell_color_2nd_highest).strip()
            if higher_is_better and 2 not in cell_color_ranks:
                cell_color_ranks[2] = cell_color_2nd_highest

        cell_color_2nd_lowest = data.get("cell_color_second_lowest") or data.get(
            "bg_second_lowest"
        )
        if cell_color_2nd_lowest is not None:
            cell_color_2nd_lowest = str(cell_color_2nd_lowest).strip()
            if not higher_is_better and 2 not in cell_color_ranks:
                cell_color_ranks[2] = cell_color_2nd_lowest

        decimals = data.get("decimals")
        if decimals is not None:
            decimals = int(decimals)

        # Auto-scaling and unit options
        auto_scale = (
            data.get("auto_scale")
            or data.get("si_prefix")
            or data.get("si")
            or data.get("si_scaling")
        )
        if isinstance(auto_scale, str):
            auto_scale = auto_scale.strip().lower()

        scale = data.get("scale") or data.get("scale_factor") or data.get("multiplier")
        if scale is not None:
            scale = float(scale)

        unit = data.get("unit") or data.get("units") or data.get("suffix")
        if unit is not None:
            unit = str(unit)

        styles_raw = data.get("styles", [])
        styles: list[str] = []
        if isinstance(styles_raw, str):
            styles = [
                s.strip().lower()
                for s in styles_raw.replace(",", "|").split("|")
                if s.strip()
            ]
        elif isinstance(styles_raw, (list, tuple)):
            styles = [str(s).strip().lower() for s in styles_raw if str(s).strip()]

        custom_format = data.get("custom_format") or data.get("format")

        def _parse_highlight_list(
            val: Any, default_flags: list[bool], default_names: list[str]
        ) -> list[str]:
            res: list[str] = []
            for flag, flag_name in zip(default_flags, default_names):
                if flag and flag_name not in res:
                    res.append(flag_name)
            if val:
                if isinstance(val, str):
                    for part in val.replace(",", "|").split("|"):
                        p = part.strip().lower()
                        if p and p not in res:
                            res.append(p)
                elif isinstance(val, (list, tuple)):
                    for item in val:
                        p = str(item).strip().lower()
                        if p and p not in res:
                            res.append(p)
                elif isinstance(val, bool) and val:
                    if "bold" not in res:
                        res.append("bold")
            return res

        hl_highest = _parse_highlight_list(
            data.get("highlight_highest"),
            [bold_highest, underline_highest],
            ["bold", "underline"],
        )
        hl_lowest = _parse_highlight_list(
            data.get("highlight_lowest"),
            [bold_lowest, underline_lowest],
            ["bold", "underline"],
        )
        hl_2nd_highest = _parse_highlight_list(
            data.get("highlight_second_highest"), [], []
        )
        hl_2nd_lowest = _parse_highlight_list(
            data.get("highlight_second_lowest"), [], []
        )

        return cls(
            name=name,
            higher_is_better=higher_is_better,
            bold=bold_ranks,
            underline=underline_ranks,
            color=static_color,
            color_ranks=color_ranks,
            cell_color=static_cell_color,
            cell_color_ranks=cell_color_ranks,
            decimals=decimals,
            auto_scale=auto_scale,
            scale=scale,
            unit=unit,
            styles=styles,
            custom_format=custom_format,
            bold_highest=bold_highest,
            bold_lowest=bold_lowest,
            underline_highest=underline_highest,
            underline_lowest=underline_lowest,
            highlight_highest=hl_highest,
            highlight_lowest=hl_lowest,
            highlight_second_highest=hl_2nd_highest,
            highlight_second_lowest=hl_2nd_lowest,
            cell_color_highest=cell_color_highest,
            cell_color_lowest=cell_color_lowest,
            cell_color_second_highest=cell_color_2nd_highest,
            cell_color_second_lowest=cell_color_2nd_lowest,
        )


class RulesConfig:
    """Manages collection of GroupRules loaded from a YAML/JSON file or dictionary."""

    def __init__(
        self,
        groups: Mapping[str, GroupRule] | None = None,
        default_rule: GroupRule | None = None,
    ) -> None:
        self.groups: dict[str, GroupRule] = dict(groups) if groups else {}
        self.default_rule: GroupRule = default_rule or GroupRule(name="default")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RulesConfig:
        groups: dict[str, GroupRule] = {}
        default_rule: GroupRule | None = None

        # Look for "groups" subkey or top-level group mappings
        groups_dict = data.get("groups", data)
        if isinstance(groups_dict, Mapping):
            for k, v in groups_dict.items():
                if k == "default":
                    default_rule = GroupRule.from_dict(
                        "default", v if isinstance(v, Mapping) else None
                    )
                elif isinstance(v, Mapping):
                    groups[k] = GroupRule.from_dict(k, v)

        if (
            default_rule is None
            and "default" in data
            and isinstance(data["default"], Mapping)
        ):
            default_rule = GroupRule.from_dict("default", data["default"])

        return cls(groups=groups, default_rule=default_rule)

    @classmethod
    def from_file(cls, path: str | Path, encoding: str = "utf-8") -> RulesConfig:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Rules configuration file not found: {path}")

        content = file_path.read_text(encoding=encoding)
        return cls.from_yaml(content)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> RulesConfig:
        loaded = yaml.safe_load(yaml_content)
        if not isinstance(loaded, Mapping):
            return cls()
        return cls.from_dict(loaded)

    def get_rule(self, group_name: str) -> GroupRule:
        """Get rule for group name, returning default rule if not specifically defined."""
        clean_name = str(group_name).strip()
        if clean_name in self.groups:
            return self.groups[clean_name]
        # Case-insensitive search
        for k, v in self.groups.items():
            if k.lower() == clean_name.lower():
                return v
        return self.default_rule

    def has_group(self, group_name: str) -> bool:
        clean_name = str(group_name).strip()
        return clean_name in self.groups or any(
            k.lower() == clean_name.lower() for k in self.groups
        )

    def __contains__(self, group_name: str) -> bool:
        return self.has_group(group_name)

    def __getitem__(self, group_name: str) -> GroupRule:
        return self.get_rule(group_name)


def load_rules(
    source: str | Path | Mapping[str, Any] | RulesConfig | None,
) -> RulesConfig:
    """Helper function to load RulesConfig from file path, YAML string, dict, or existing RulesConfig."""
    if source is None:
        return RulesConfig()
    if isinstance(source, RulesConfig):
        return source
    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.is_file():
            return RulesConfig.from_file(p)
        elif isinstance(source, str) and ("\n" in source or ":" in source):
            return RulesConfig.from_yaml(source)
        else:
            raise FileNotFoundError(f"Rules file not found: {source}")
    if isinstance(source, Mapping):
        return RulesConfig.from_dict(source)
    raise TypeError(f"Unsupported rules source type: {type(source)}")
