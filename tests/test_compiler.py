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
