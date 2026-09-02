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
    decimals: int | None = None
    bold_highest: bool = False
    bold_lowest: bool = False
    underline_highest: bool = False
    underline_lowest: bool = False
    highlight_highest: list[str] = field(default_factory=list)
    highlight_lowest: list[str] = field(default_factory=list)
    highlight_second_highest: list[str] = field(default_factory=list)
    highlight_second_lowest: list[str] = field(default_factory=list)
    color: str | None = None
    cell_color: str | None = None
    cell_color_highest: str | None = None
    cell_color_lowest: str | None = None
    cell_color_second_highest: str | None = None
    cell_color_second_lowest: str | None = None
    styles: list[str] = field(default_factory=list)
    custom_format: str | None = None

    @classmethod
    def from_dict(cls, name: str, data: Mapping[str, Any] | None) -> GroupRule:
        if not data:
            return cls(name=name)

        decimals = data.get("decimals")
        if decimals is not None:
            decimals = int(decimals)

        bold_highest = bool(data.get("bold_highest", False))
        bold_lowest = bool(data.get("bold_lowest", False))
        underline_highest = bool(data.get("underline_highest", False))
        underline_lowest = bool(data.get("underline_lowest", False))

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

        color = data.get("color")
        if color is not None:
            color = str(color).strip()

        # Cell background colors (aliases: cell_color, bg_color, background_color)
        cell_color = (
            data.get("cell_color")
            or data.get("bg_color")
            or data.get("background_color")
        )
        if cell_color is not None:
            cell_color = str(cell_color).strip()

        cell_color_highest = (
            data.get("cell_color_highest")
            or data.get("bg_color_highest")
            or data.get("bg_highest")
        )
        if cell_color_highest is not None:
            cell_color_highest = str(cell_color_highest).strip()

        cell_color_lowest = (
            data.get("cell_color_lowest")
            or data.get("bg_color_lowest")
            or data.get("bg_lowest")
        )
        if cell_color_lowest is not None:
            cell_color_lowest = str(cell_color_lowest).strip()

        cell_color_2nd_highest = data.get("cell_color_second_highest") or data.get(
            "bg_second_highest"
        )
        if cell_color_2nd_highest is not None:
            cell_color_2nd_highest = str(cell_color_2nd_highest).strip()

        cell_color_2nd_lowest = data.get("cell_color_second_lowest") or data.get(
            "bg_second_lowest"
        )
        if cell_color_2nd_lowest is not None:
            cell_color_2nd_lowest = str(cell_color_2nd_lowest).strip()

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

        return cls(
            name=name,
            decimals=decimals,
            bold_highest=bold_highest or ("bold" in hl_highest),
            bold_lowest=bold_lowest or ("bold" in hl_lowest),
            underline_highest=underline_highest or ("underline" in hl_highest),
            underline_lowest=underline_lowest or ("underline" in hl_lowest),
            highlight_highest=hl_highest,
            highlight_lowest=hl_lowest,
            highlight_second_highest=hl_2nd_highest,
            highlight_second_lowest=hl_2nd_lowest,
            color=color,
            cell_color=cell_color,
            cell_color_highest=cell_color_highest,
            cell_color_lowest=cell_color_lowest,
            cell_color_second_highest=cell_color_2nd_highest,
            cell_color_second_lowest=cell_color_2nd_lowest,
            styles=styles,
            custom_format=custom_format,
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
