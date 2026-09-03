"""Tests for LaTeX compilation and image preview utilities."""

from pathlib import Path
import pytest
from latex_table_generator.compiler import (
    compile_table,
    create_standalone_document,
    is_pdflatex_available,
    is_pdftoppm_available,
)


def test_create_standalone_document():
    snippet = "\\begin{tabular}{cc} A & B \\end{tabular}"
    doc = create_standalone_document(snippet)
    assert "\\documentclass" in doc
    assert "\\usepackage{booktabs}" in doc
    assert snippet in doc


@pytest.mark.skipif(not is_pdflatex_available(), reason="pdflatex not available")
def test_compile_table_pdf(tmp_path: Path):
    table_snippet = """\\begin{tabular}{cc}
\\toprule
Model & Accuracy \\\\
\\midrule
M1 & 0.85 \\ensuremath{\\pm} 0.02 \\\\
\\bottomrule
\\end{tabular}"""

    pdf_out = tmp_path / "table.pdf"
    res_pdf, res_png = compile_table(table_snippet, output_pdf=pdf_out)
    assert res_pdf is not None
    assert pdf_out.exists()
    assert pdf_out.stat().st_size > 0


@pytest.mark.skipif(
    not (is_pdflatex_available() and is_pdftoppm_available()),
    reason="pdflatex or pdftoppm not available",
)
def test_compile_table_png(tmp_path: Path):
    table_snippet = """\\begin{tabular}{cc}
\\toprule
Model & Score \\\\
\\midrule
M1 & 0.95 \\\\
\\bottomrule
\\end{tabular}"""

    png_out = tmp_path / "table.png"
    res_pdf, res_png = compile_table(table_snippet, output_png=png_out, dpi=150)
    assert res_png is not None
    assert png_out.exists()
    assert png_out.stat().st_size > 0


@pytest.mark.skipif(
    not (is_pdflatex_available() and is_pdftoppm_available()),
    reason="pdflatex or pdftoppm not available",
)
def test_compile_wide_table(tmp_path: Path):
    # 15 columns table
    headers = " & ".join([f"Column {i}" for i in range(15)])
    values = " & ".join([f"Value {i} (0.123)" for i in range(15)])
    table_snippet = f"""\\begin{{table}}
\\centering
\\caption{{Very Wide Benchmark Table}}
\\begin{{tabular}}{{{"c" * 15}}}
\\toprule
{headers} \\\\
\\midrule
{values} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}"""

    pdf_out = tmp_path / "wide_table.pdf"
    png_out = tmp_path / "wide_table.png"
    res_pdf, res_png = compile_table(
        table_snippet, output_pdf=pdf_out, output_png=png_out, dpi=150
    )
    assert res_pdf is not None
    assert res_png is not None
    assert pdf_out.exists()
    assert png_out.exists()


@pytest.mark.skipif(
    not (is_pdflatex_available() and is_pdftoppm_available()),
    reason="pdflatex or pdftoppm not available",
)
def test_compile_table_with_threeparttable(tmp_path: Path):
    table_snippet = """\\begin{table}
\\centering
\\begin{threeparttable}
\\caption{A long caption describing the benchmark results that automatically wraps to the exact width of the table rather than stretching out.}
\\begin{tabular}{cc}
\\toprule
Model & Score \\\\
\\midrule
M1 & 0.95 \\\\
\\bottomrule
\\end{tabular}
\\end{threeparttable}
\\end{table}"""

    pdf_out = tmp_path / "tpt_table.pdf"
    png_out = tmp_path / "tpt_table.png"
    res_pdf, res_png = compile_table(
        table_snippet, output_pdf=pdf_out, output_png=png_out, dpi=150
    )
    assert res_pdf is not None
    assert res_png is not None
    assert pdf_out.exists()
    assert png_out.exists()
