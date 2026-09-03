"""Command-line interface for generating LaTeX tables from CSV metrics and template files."""

from __future__ import annotations

import argparse
import sys

from latex_table_generator.compiler import compile_table
from latex_table_generator.generator import generate_latex_table


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="latex-table-generator",
        description="Generate LaTeX tables from CSV metrics and custom template files.",
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to the .csv file containing metrics.",
    )
    parser.add_argument(
        "template_path",
        type=str,
        help="Path to the template .txt or .tex file containing the table layout.",
    )
    parser.add_argument(
        "-r",
        "--rules",
        type=str,
        default=None,
        help="Path to YAML/JSON rules configuration file defining group formatting rules.",
    )
    parser.add_argument(
        "-d",
        "--decimals",
        type=int,
        default=None,
        help="Default number of decimal places for numeric metrics if not specified in group rules.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to output .tex file (if not specified, prints to stdout).",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Compile table directly to a PDF file.",
    )
    parser.add_argument(
        "--png",
        type=str,
        default=None,
        help="Render table directly to a PNG image preview.",
    )
    parser.add_argument(
        "--pm-symbol",
        type=str,
        default=r"\ensuremath{\pm}",
        help=r"LaTeX symbol to use for uncertainties (default: '\ensuremath{\pm}').",
    )
    parser.add_argument(
        "--align",
        action="store_true",
        help="Neatly align '&' columns in the output LaTeX table.",
    )
    parser.add_argument(
        "--no-align-numbers",
        dest="align_numbers",
        action="store_false",
        default=True,
        help="Disable automatic column number alignment (phantom minus & digits).",
    )
    parser.add_argument(
        "--delimiter",
        type=str,
        default=",",
        help="CSV delimiter (default: ',').",
    )
    parser.add_argument(
        "--index-col",
        type=str,
        default="0",
        help="Index column position or column name in CSV (default: 0).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="latex-table-generator 0.1.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    # Parse index_col as int if numeric
    index_col: int | str = args.index_col
    if isinstance(index_col, str) and index_col.isdigit():
        index_col = int(index_col)

    try:
        table_output = generate_latex_table(
            csv_path=args.csv_path,
            template_path=args.template_path,
            rules_path=args.rules,
            decimals=args.decimals,
            output_path=args.output,
            pm_symbol=args.pm_symbol,
            align_columns=args.align,
            align_numbers=args.align_numbers,
            delimiter=args.delimiter,
            index_col=index_col,
        )

        if args.output:
            print(f"Successfully generated LaTeX table: {args.output}")
        elif not args.pdf and not args.png:
            print(table_output)

        if args.pdf or args.png:
            compile_table(
                table_source=table_output,
                output_pdf=args.pdf,
                output_png=args.png,
            )
            if args.pdf:
                print(f"Compiled PDF: {args.pdf}")
            if args.png:
                print(f"Rendered PNG: {args.png}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
