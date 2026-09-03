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
    italic: list[int] = field(default_factory=list)
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
    align_numbers: bool | None = None
    standard_error_of_mean: int | None = None

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

        # 2. Parse rank lists (supports integer like `bold: 1`, `bold: -1`, list like `bold: [1, -1]`, boolean `bold: true`)
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
                    try:
                        res.append(int(p_str))
                    except ValueError:
                        pass
                return res
            if isinstance(val, (list, tuple)):
                res = []
                for item in val:
                    if isinstance(item, int):
                        res.append(item)
                    elif isinstance(item, str):
                        try:
                            res.append(int(item.strip()))
                        except ValueError:
                            pass
                    elif isinstance(item, bool) and item:
                        res.append(1)
                return res
            return []

        bold_ranks = _parse_rank_list(data.get("bold"))
        underline_ranks = _parse_rank_list(data.get("underline"))
        italic_ranks = _parse_rank_list(data.get("italic"))

        # 3. Parse text colors (static string or rank dict, supports negative ranks like -1)
        color_ranks: dict[int, str] = {}
        raw_color = data.get("color") or data.get("color_ranks")
        static_color: str | None = None
        if isinstance(raw_color, dict):
            for k, v in raw_color.items():
                try:
                    k_int = int(str(k).strip())
                    if v:
                        color_ranks[k_int] = str(v).strip()
                except (ValueError, TypeError):
                    pass
        elif raw_color is not None:
            static_color = str(raw_color).strip()

        for k, v in data.items():
            k_lower = k.lower()
            if k_lower.startswith("color_") and k_lower != "color_ranks":
                suffix = k_lower[6:].strip()
                try:
                    color_ranks[int(suffix)] = str(v).strip()
                except (ValueError, TypeError):
                    pass

        # 4. Parse cell background colors (static string or rank dict, supports negative ranks like -1)
        cell_color_ranks: dict[int, str] = {}
        raw_cell_color = (
            data.get("cell_color")
            or data.get("cell_color_ranks")
            or data.get("bg_color")
            or data.get("background_color")
        )
        static_cell_color: str | None = None
        if isinstance(raw_cell_color, dict):
            for k, v in raw_cell_color.items():
                try:
                    k_int = int(str(k).strip())
                    if v:
                        cell_color_ranks[k_int] = str(v).strip()
                except (ValueError, TypeError):
                    pass
        elif raw_cell_color is not None:
            static_cell_color = str(raw_cell_color).strip()

        for k, v in data.items():
            k_lower = k.lower()
            if (
                (k_lower.startswith("cell_color_") and k_lower != "cell_color_ranks")
                or (k_lower.startswith("bg_color_") and k_lower != "bg_color_ranks")
                or k_lower.startswith("bg_")
            ):
                suffix = k_lower.rsplit("_", 1)[1].strip()
                try:
                    cell_color_ranks[int(suffix)] = str(v).strip()
                except (ValueError, TypeError):
                    pass

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

        align_numbers = data.get("align_numbers")
        if align_numbers is None:
            align_numbers = data.get("align_decimals")
        if align_numbers is not None:
            align_numbers = bool(align_numbers)

        sem_raw = None
        for key in ("standard_error_of_mean", "sem", "standard_error"):
            if key in data and data[key] is not None:
                sem_raw = data[key]
                break
        standard_error_of_mean: int | None = None
        if sem_raw is not None and str(sem_raw).strip() != "":
            try:
                sem_int = int(str(sem_raw).strip())
                if sem_int <= 0:
                    raise ValueError(
                        f"standard_error_of_mean must be a positive integer, got {sem_int}"
                    )
                standard_error_of_mean = sem_int
            except ValueError as e:
                if "positive integer" in str(e):
                    raise
                raise ValueError(
                    f"Invalid standard_error_of_mean value: {sem_raw}. Must be a positive integer."
                ) from e

        return cls(
            name=name,
            higher_is_better=higher_is_better,
            bold=bold_ranks,
            underline=underline_ranks,
            italic=italic_ranks,
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
            align_numbers=align_numbers,
            standard_error_of_mean=standard_error_of_mean,
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
