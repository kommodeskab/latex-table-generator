"""Example demonstrating how to use latex_table_generator."""

from pathlib import Path
from latex_table_generator import compile_table, generate_latex_table

# File paths
curr_dir = Path(__file__).parent
csv_path = curr_dir / "metrics.csv"
template_path = curr_dir / "template.txt"
rules_path = curr_dir / "rules.yaml"
output_tex_path = curr_dir / "table_output.tex"
output_pdf_path = curr_dir / "table_output.pdf"
output_png_path = curr_dir / "table_output.png"

# 1. Generate LaTeX table code using group rules
latex_code = generate_latex_table(
    csv_path=csv_path,
    template_path=template_path,
    rules_path=rules_path,
    output_path=output_tex_path,
    align_columns=True,
)

print("Generated LaTeX Table:")
print("-" * 60)
print(latex_code)
print("-" * 60)
print(f"Saved LaTeX source to: {output_tex_path}")

# 2. Render and compile directly to PDF and PNG image preview
compile_table(
    table_source=output_tex_path,
    output_pdf=output_pdf_path,
    output_png=output_png_path,
    dpi=300,
)
print(f"Compiled PDF: {output_pdf_path}")
print(f"Rendered PNG preview: {output_png_path}")
