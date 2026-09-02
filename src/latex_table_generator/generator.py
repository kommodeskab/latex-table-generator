"""High-level API for generating LaTeX tables from metrics CSV and template files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from latex_table_generator.metrics import MetricsStore, load_metrics
from latex_table_generator.rules import RulesConfig, load_rules
from latex_table_generator.template import TemplateRenderer


def generate_latex_table(
    csv_path: str | Path | Mapping[str, Mapping[str, Any]] | MetricsStore | Any,
    template_path: str | Path,
    rules_path: str | Path | RulesConfig | Mapping[str, Any] | None = None,
    rules: str | Path | RulesConfig | Mapping[str, Any] | None = None,
    decimals: int | None = None,
    output_path: str | Path | None = None,
    pm_symbol: str = r"\ensuremath{\pm}",
    align_columns: bool = False,
    delimiter: str = ",",
    index_col: int | str = 0,
    encoding: str = "utf-8",
) -> str:
    """Generate a LaTeX table from a CSV file containing metrics and a template file.

    Parameters
    ----------
    csv_path : str, Path, Mapping, or MetricsStore
        Path to the .csv file containing metrics, or an existing MetricsStore / dictionary.
    template_path : str or Path
        Path to the template .txt / .tex file, or template string content.
    rules_path : str, Path, dict, or RulesConfig, optional
        Path to the YAML/JSON rules file containing per-group formatting rules.
    rules : str, Path, dict, or RulesConfig, optional
        Alias for rules_path.
    decimals : int, optional
        Default number of decimal places if not specified in group rules.
    output_path : str or Path, optional
        If provided, the generated LaTeX table will be saved to this file path.
    pm_symbol : str, default r"\\ensuremath{\\pm}"
        The LaTeX symbol used to render '+-' for uncertainties.
    align_columns : bool, default False
        Whether to align '&' column separators neatly in the output LaTeX table.
    delimiter : str, default ","
        CSV delimiter.
    index_col : int or str, default 0
        Column index or column name to use as row keys in the CSV.
    encoding : str, default "utf-8"
        File encoding when reading and writing files.

    Returns
    -------
    str
        The rendered LaTeX table as a string.

    Examples
    --------
    >>> table = generate_latex_table("metrics.csv", "template.txt", rules_path="rules.yaml")
    >>> print(table)
    """
    # Load metrics
    metrics = load_metrics(
        csv_path, delimiter=delimiter, index_col=index_col, encoding=encoding
    )

    # Load rules (either from rules_path or rules)
    effective_rules = load_rules(rules_path if rules_path is not None else rules)

    # Initialize renderer
    renderer = TemplateRenderer(
        metrics=metrics,
        rules=effective_rules,
        decimals=decimals,
        pm_symbol=pm_symbol,
        align_columns=align_columns,
    )

    # Check if template_path is a path to an existing file or a raw template string
    if isinstance(template_path, str) and (
        "\n" in template_path or "&" in template_path or "{" in template_path
    ):
        result = renderer.render(template_path)
        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(result, encoding=encoding)
        return result
    elif isinstance(template_path, (str, Path)):
        template_p = Path(template_path)
        if template_p.exists() and template_p.is_file():
            return renderer.render_file(
                template_p, output_path=output_path, encoding=encoding
            )
        else:
            raise FileNotFoundError(f"Template file not found: {template_path}")

    raise TypeError(f"Unsupported template_path type: {type(template_path)}")


# Alias for convenience
generate_table = generate_latex_table


class TableGenerator:
    """Class-based interface for generating LaTeX tables with reusable metrics and rules configuration."""

    def __init__(
        self,
        metrics: str | Path | Mapping[str, Mapping[str, Any]] | MetricsStore | Any,
        rules: str | Path | RulesConfig | Mapping[str, Any] | None = None,
        decimals: int | None = None,
        pm_symbol: str = r"\ensuremath{\pm}",
        align_columns: bool = False,
        delimiter: str = ",",
        index_col: int | str = 0,
    ) -> None:
        self.metrics = load_metrics(metrics, delimiter=delimiter, index_col=index_col)
        self.rules = load_rules(rules)
        self.decimals = decimals
        self.pm_symbol = pm_symbol
        self.align_columns = align_columns

    @classmethod
    def from_csv(
        cls,
        csv_path: str | Path,
        rules_path: str | Path | None = None,
        decimals: int | None = None,
        pm_symbol: str = r"\ensuremath{\pm}",
        align_columns: bool = False,
        delimiter: str = ",",
        index_col: int | str = 0,
    ) -> TableGenerator:
        """Create a TableGenerator directly from a CSV file and optional rules file."""
        return cls(
            metrics=csv_path,
            rules=rules_path,
            decimals=decimals,
            pm_symbol=pm_symbol,
            align_columns=align_columns,
            delimiter=delimiter,
            index_col=index_col,
        )

    def render(self, template_str: str) -> str:
        """Render a LaTeX table from a template string."""
        renderer = TemplateRenderer(
            metrics=self.metrics,
            rules=self.rules,
            decimals=self.decimals,
            pm_symbol=self.pm_symbol,
            align_columns=self.align_columns,
        )
        return renderer.render(template_str)

    def render_file(
        self,
        template_path: str | Path,
        output_path: str | Path | None = None,
        encoding: str = "utf-8",
    ) -> str:
        """Render a LaTeX table from a template file and optionally save to output_path."""
        renderer = TemplateRenderer(
            metrics=self.metrics,
            rules=self.rules,
            decimals=self.decimals,
            pm_symbol=self.pm_symbol,
            align_columns=self.align_columns,
        )
        return renderer.render_file(
            template_path, output_path=output_path, encoding=encoding
        )
