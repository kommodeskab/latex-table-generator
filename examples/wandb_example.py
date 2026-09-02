"""Example demonstrating how to fetch metrics from Weights & Biases (WandB) and generate a LaTeX table."""

from pathlib import Path
from latex_table_generator import (
    compile_table,
    fetch_wandb_metrics,
    generate_latex_table,
)

curr_dir = Path(__file__).parent
output_csv = curr_dir / "wandb_metrics.csv"
output_tex = curr_dir / "wandb_table.tex"
output_png = curr_dir / "wandb_table.png"
output_pdf = curr_dir / "wandb_table.pdf"

# 1. Fetch metrics from WandB and save to CSV
print("Fetching metrics from WandB...")
csv_content = fetch_wandb_metrics(
    run_ids=["300826143817", "300826145103"],
    metrics=["test_loss"],
    output_path=output_csv,
    # Optional: custom model names (leave empty/None to use WandB run names)
    run_names=[],
    # Optional: alternative column names for metrics (leave empty/None to use metric names)
    metric_names=["loss"],
)

print(f"Saved WandB metrics to: {output_csv}")
print("CSV Preview:")
print(csv_content)

# 2. Template using the fetched WandB metrics
template = r"""\begin{table}[htbp]
\centering
\caption{Model performance comparison from WandB runs.}
\label{tab:wandb_comparison}
\begin{tabular}{lcc}
\toprule
\textbf{Model} & \textbf{Run ID} & \textbf{Test Loss} \\
\midrule
SNR Model & 300826143817 & {snr loss.loss:.2f} \\
Drifting Model & 300826145103 & {drifting loss.loss:.2f} \\
\bottomrule
\end{tabular}
\end{table}
"""

# 3. Generate LaTeX table
latex_code = generate_latex_table(
    csv_path=output_csv,
    template_path=template,
    output_path=output_tex,
    align_columns=True,
)

print("-" * 60)
print("Generated LaTeX Table:")
print(latex_code)
print("-" * 60)

# 4. Compile to PDF and PNG
compile_table(
    table_source=output_tex,
    output_pdf=output_pdf,
    output_png=output_png,
)
print(f"Compiled PDF: {output_pdf}")
print(f"Rendered PNG: {output_png}")
