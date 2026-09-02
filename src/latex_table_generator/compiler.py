"""LaTeX compilation and image preview utilities."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence


def is_pdflatex_available() -> bool:
    """Check if pdflatex or xelatex is installed and available in PATH."""
    return shutil.which("pdflatex") is not None or shutil.which("xelatex") is not None


def is_pdftoppm_available() -> bool:
    """Check if pdftoppm is installed and available in PATH."""
    return shutil.which("pdftoppm") is not None


def create_standalone_document(
    table_latex: str,
    extra_packages: Sequence[str] | None = None,
) -> str:
    """Wrap table LaTeX snippet in a minimal standalone document for compilation."""
    packages = ["booktabs", "amsmath", "amssymb", "tabularx", "multirow"]
    if extra_packages:
        packages.extend(extra_packages)

    unique_packages = []
    for pkg in packages:
        if pkg not in unique_packages:
            unique_packages.append(pkg)

    pkg_imports = "\n".join(f"\\usepackage{{{pkg}}}" for pkg in unique_packages)

    return f"""\\documentclass[preview,border=10pt]{{standalone}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[dvipsnames,table]{{xcolor}}
{pkg_imports}
\\begin{{document}}
{table_latex}
\\end{{document}}
"""


def compile_table(
    table_source: str | Path,
    output_pdf: str | Path | None = None,
    output_png: str | Path | None = None,
    dpi: int = 300,
    engine: str = "pdflatex",
    extra_packages: Sequence[str] | None = None,
) -> tuple[Path | None, Path | None]:
    """Compile LaTeX table to PDF and/or PNG preview.

    Parameters
    ----------
    table_source : str or Path
        LaTeX snippet string or path to a .tex file containing the table.
    output_pdf : str or Path, optional
        Destination path for compiled PDF.
    output_png : str or Path, optional
        Destination path for rendered PNG image.
    dpi : int, default 300
        Resolution (DPI) for PNG rendering.
    engine : str, default "pdflatex"
        LaTeX engine to use ("pdflatex", "xelatex", or "lualatex").
    extra_packages : list of str, optional
        Additional LaTeX packages to include.

    Returns
    -------
    tuple of (pdf_path, png_path)
    """
    compiler = (
        shutil.which(engine) or shutil.which("pdflatex") or shutil.which("xelatex")
    )
    if not compiler:
        raise RuntimeError(
            "No LaTeX compiler (pdflatex / xelatex) found in PATH. "
            "Please install TeX Live, MacTeX, or MiKTeX to compile tables."
        )

    # Read table source if it's a file
    if isinstance(table_source, Path) or (
        isinstance(table_source, str) and Path(table_source).is_file()
    ):
        table_code = Path(table_source).read_text(encoding="utf-8")
    else:
        table_code = str(table_source)

    # Check if table_code already contains \documentclass
    if "\\documentclass" in table_code:
        full_doc = table_code
    else:
        full_doc = create_standalone_document(table_code, extra_packages=extra_packages)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tex_file = tmp_path / "table_doc.tex"
        tex_file.write_text(full_doc, encoding="utf-8")

        # Compile with pdflatex
        cmd = [
            compiler,
            "-interaction=nonstopmode",
            "-output-directory",
            str(tmp_path),
            str(tex_file),
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        pdf_generated = tmp_path / "table_doc.pdf"
        if not pdf_generated.exists():
            log_file = tmp_path / "table_doc.log"
            log_text = (
                log_file.read_text(encoding="utf-8", errors="replace")
                if log_file.exists()
                else result.stdout
            )
            raise RuntimeError(f"LaTeX compilation failed:\n{log_text[-1500:]}")

        # Copy PDF to target if requested
        final_pdf: Path | None = None
        if output_pdf:
            final_pdf = Path(output_pdf)
            final_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf_generated, final_pdf)

        # Convert to PNG if requested
        final_png: Path | None = None
        if output_png:
            final_png = Path(output_png)
            final_png.parent.mkdir(parents=True, exist_ok=True)

            pdftoppm_bin = shutil.which("pdftoppm")
            if pdftoppm_bin:
                prefix = tmp_path / "page"
                subprocess.run(
                    [
                        pdftoppm_bin,
                        "-png",
                        "-r",
                        str(dpi),
                        "-singlefile",
                        str(pdf_generated),
                        str(prefix),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                rendered_page = tmp_path / "page.png"
                if rendered_page.exists():
                    convert_bin = shutil.which("convert")
                    if convert_bin:
                        # Trim extra whitespace around the table
                        subprocess.run(
                            [
                                convert_bin,
                                str(rendered_page),
                                "-trim",
                                "+repage",
                                "-bordercolor",
                                "white",
                                "-border",
                                "15",
                                str(final_png),
                            ],
                            check=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                    else:
                        shutil.copyfile(rendered_page, final_png)
            else:
                raise RuntimeError(
                    "pdftoppm is not installed; cannot convert PDF to PNG."
                )

        return final_pdf, final_png
