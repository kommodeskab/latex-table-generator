"""LaTeX Table Generator from CSV metrics and template files."""

from __future__ import annotations

from latex_table_generator.compiler import (
    compile_table,
    is_pdflatex_available,
    is_pdftoppm_available,
)
from latex_table_generator.formatter import format_uncertainty, format_value
from latex_table_generator.generator import (
    TableGenerator,
    generate_latex_table,
    generate_table,
)
from latex_table_generator.metrics import (
    MetricNotFoundError,
    MetricsStore,
    load_metrics,
)
from latex_table_generator.rules import GroupRule, RulesConfig, load_rules
from latex_table_generator.template import TemplateRenderer, align_latex_table

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "generate_latex_table",
    "generate_table",
    "TableGenerator",
    "MetricsStore",
    "load_metrics",
    "MetricNotFoundError",
    "TemplateRenderer",
    "align_latex_table",
    "format_value",
    "format_uncertainty",
    "compile_table",
    "is_pdflatex_available",
    "is_pdftoppm_available",
    "GroupRule",
    "RulesConfig",
    "load_rules",
]
