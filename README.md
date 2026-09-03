# LaTeX Table Generator (`latex-table-generator`)

A lightweight, flexible Python package to automatically generate publication-ready LaTeX tables from `.csv` metric files, custom `.txt` template files, and reusable `.yaml` rule files.

---

## Features

- **CSV Metrics Integration**: Load floating-point metrics with row and column headers directly from `.csv` files.
- **Intuitive Placeholders**: Insert metric values into table cells using `{row.column}` syntax.
- **Built-in Uncertainty Support**: Format mean and standard deviation pairs effortlessly using `{row.mean +- row.std}`.
- **Cell Grouping & Rule Files**: Assign cells to groups (e.g. `[accuracy]`, `[latency]`, `[accuracy, best_model]`) and define formatting rules in a reusable `.yaml` file:
  - **Decimals per group**: Set individual decimal precision for each group.
  - **Extremum Highlighting**: Automatically bold and/or underline the highest or lowest numbers in each group (ignoring uncertainties for comparison).
  - **Group Text Colors**: Assign custom colors to groups (`blue`, `red`, `ForestGreen`, `#FF5733`).
  - **Multi-group Cells**: Cells can belong to multiple groups and inherit combined rules.
- **Automatic Column Number Alignment**: Automatically aligns decimal points, minus signs, and uncertainty symbols across rows (via LaTeX `\hphantom{-}` and digit padding), ensuring publication-grade vertical alignment even when columns mix positive and negative numbers.
- **LaTeX Styling & Preservations**: Native support for styling modifiers (`:bold`, `:italic`, `:underline`, `:math`) while preserving all regular LaTeX commands (`\textbf{...}`, `\begin{tabular}`, `\begin{threeparttable}`, `\caption{...}`, `\toprule`, etc.).
- **Automatic Caption Wrapping**: Built-in support for `threeparttable` so long captions cleanly wrap to the exact width of the table.
- **Neat Column Alignment**: Optional `--align` / `align_columns=True` to neatly format and pad table columns in LaTeX source code.
- **Direct PDF & PNG Rendering**: Compile tables directly to PDF and trimmed PNG preview images with `compile_table()` or CLI `--pdf` / `--png`.

---

## Installation

```bash
pip install .
```

Or using `uv`:

```bash
uv pip install .
```

---

## Quickstart

### 1. Metrics File (`metrics.csv`)

```csv
model,acc_mean,acc_std,f1_mean,f1_std,latency
res18,0.7645,0.0123,0.7512,0.0145,12.4
res50,0.8123,0.0098,0.8045,0.0112,24.8
vit,0.8654,0.0067,0.8591,0.0078,45.2
swin,0.8812,0.0054,0.8765,0.0061,52.1
```

### 2. Group Rules Configuration (`rules.yaml`)

Define reusable formatting rules for each group:

```yaml
groups:
  # Accuracy column: higher is better, rank 1 is bold, rank 2 is underlined, blue color
  accuracy:
    higher_is_better: true
    bold: 1
    underline: 2
    decimals: 2
    color: "blue"

  # F1 column: higher is better, rank 1 is bold, navy color
  f1:
    higher_is_better: true
    bold: 1
    decimals: 2
    color: "NavyBlue"

  # Latency column: lower is better (faster is better!), rank 1 is bold
  latency:
    higher_is_better: false
    bold: 1
    decimals: 1
    color: "darkgray"

  # Special tag that can be added to any cell
  top_performer:
    color: "ForestGreen"

default:
  decimals: 2
```

### 3. Table Template (`template.txt`)

Assign cells to groups using `[group_name]{...}` or `{... | group_name}`:

```latex
\begin{table}[htbp]
\centering
\caption{Classification performance comparison.}
\label{tab:model_comparison}
\begin{tabular}{lccc}
\toprule
\textbf{Model} & \textbf{Accuracy} & \textbf{F1-Score} & \textbf{Latency (ms)} \\
\midrule
ResNet-18 & [accuracy]{res18.acc_mean +- res18.acc_std} & [f1]{res18.f1_mean +- res18.f1_std} & [latency]{res18.latency} \\
ResNet-50 & [accuracy]{res50.acc_mean +- res50.acc_std} & [f1]{res50.f1_mean +- res50.f1_std} & [latency]{res50.latency} \\
ViT-Base & [accuracy]{vit.acc_mean +- vit.acc_std} & [f1]{vit.f1_mean +- vit.f1_std} & [latency]{vit.latency} \\
\textbf{Swin-Transformer} & [accuracy, top_performer]{swin.acc_mean +- swin.acc_std} & [f1, top_performer]{swin.f1_mean +- swin.f1_std} & [latency]{swin.latency} \\
\bottomrule
\end{tabular}
\end{table}
```

### 4. Generate & Render in Python

```python
from latex_table_generator import compile_table, generate_latex_table

# Generate LaTeX table code
latex_code = generate_latex_table(
    csv_path="metrics.csv",
    template_path="template.txt",
    rules_path="rules.yaml",
    output_path="table.tex",
    align_columns=True,
)

# Optional: compile directly to PDF and PNG preview
compile_table(
    table_source="table.tex",
    output_pdf="table.pdf",
    output_png="table.png",
    dpi=300,
)
```

**Generated LaTeX Output:**

```latex
\begin{table}[htbp]
\centering
\caption{Classification performance comparison.}
\label{tab:model_comparison}
\begin{tabular}{lccc}
\toprule
\textbf{Model}            & \textbf{Accuracy}                                        & \textbf{F1-Score}                                         & \textbf{Latency (ms)} \\
\midrule
ResNet-18                 & \textcolor{blue}{\underline{0.76 \ensuremath{\pm} 0.01}} & \textcolor{NavyBlue}{0.75 \ensuremath{\pm} 0.01}          & \textcolor{darkgray}{\textbf{12.4}} \\
ResNet-50                 & \textcolor{blue}{0.81 \ensuremath{\pm} 0.01}             & \textcolor{NavyBlue}{0.80 \ensuremath{\pm} 0.01}          & \textcolor{darkgray}{24.8} \\
ViT-Base                  & \textcolor{blue}{0.87 \ensuremath{\pm} 0.01}             & \textcolor{NavyBlue}{0.86 \ensuremath{\pm} 0.01}          & \textcolor{darkgray}{45.2} \\
\textbf{Swin-Transformer} & \textcolor{blue}{\textbf{0.88 \ensuremath{\pm} 0.01}}    & \textcolor{NavyBlue}{\textbf{0.88 \ensuremath{\pm} 0.01}} & \textcolor{darkgray}{52.1} \\
\bottomrule
\end{tabular}
\end{table}
---

## WandB Integration

Fetch metrics directly from Weights & Biases (WandB) projects or runs and save them to CSV:

```python
from latex_table_generator import fetch_wandb_metrics

# Option A: Fetch all runs from a WandB project
fetch_wandb_metrics(
    project="denoising_test",
    metrics=["test_loss"],
    output_path="wandb_metrics.csv",
    # Optional: rename columns in CSV
    metric_names=["loss"],
    # Optional: threshold before raising a warning for large number of runs (default 50)
    warn_threshold=50,
    # Optional: show disappearing tqdm progress bar (default True)
    show_progress=True,
    # Optional: enable local disk caching to avoid repeated network requests (default True)
    use_cache=True,
    cache_dir=".wandb_cache",
)

# Option B: Fetch specific run IDs
fetch_wandb_metrics(
    run_ids=["300826143817", "300826145103"],
    metrics=["test_loss"],
    output_path="wandb_metrics.csv",
    # Optional: override model names (defaults to WandB run names)
    run_names=[],
    use_cache=True,
)
```

Generated `wandb_metrics.csv`:
```csv
model,id,loss
snr loss,300826143817,-18.646778106689453
drifting loss,300826145103,0.6875496506690979
```

---

## Grouping & Rules Syntax

### Group Tagging in Templates

| Syntax | Description | Example |
| :--- | :--- | :--- |
| `[group]{placeholder}` | Prefix group assignment | `[acc]{ModelA.acc}` |
| `[g1, g2]{placeholder}` | Multiple groups on a single cell | `[acc, best]{ModelA.acc_mean +- ModelA.acc_std}` |
| `{placeholder \| group}` | Pipe group assignment | `{ModelA.acc \| acc}` |
| `{placeholder \| g1, g2}` | Pipe with multiple groups | `{ModelA.acc \| acc, best}` |
| `[group] PlainText` | Tag plain text cell | `[header_group] Method Name` |

### YAML Rule Options

```yaml
groups:
  group_name:
    higher_is_better: true         # Direction: true for metrics like Accuracy/F1, false for Loss/Latency
    bold: 1                        # Rank(s) to bold: 1 = best, -1 = worst, [1, 2] = top 2, [1, -1] = best & worst
    underline: 2                   # Rank(s) to underline: 2 = 2nd best, -1 = worst
    italic: -2                     # Rank(s) to italicize: -1 = worst, -2 = 2nd worst
    decimals: 2                    # Fixed decimal places (e.g. 0.88)
    si_prefix: true                # Auto-scale with SI prefixes (175000000 -> 175.0M, 0.000025 -> 25.0µs)
    auto_scale: "binary"           # Auto-scale mode: true/"decimal"/"si" (base 1000) or "binary"/"iec" (base 1024)
    scale: 100                     # Multiplier applied before formatting (e.g. 100 to display percentages)
    unit: "%"                      # Unit suffix appended to values (e.g. "%", " ms", " dB", "M")
    color: "blue"                  # Static text color, or rank mapping: {1: "blue", -1: "red"}
    cell_color: "yellow!25"        # Static cell background, or rank mapping: {1: "green!15", -1: "red!15"}
    cell_color_1: "green!15"       # Convenience shortcut for rank 1 cell background
    cell_color_2: "yellow!15"      # Convenience shortcut for rank 2 cell background
    styles: ["italic"]             # Static styles applied to all cells in group (["bold", "italic", "underline"])
    custom_format: "{:.1f}"        # Optional Python format string
    align_numbers: true            # Align minus signs, decimal points, and +- signs (default: true)

default:                           # Global fallback options applied to all ungrouped/grouped cells
  decimals: 2
  align_numbers: true
```

#### Rule Options Reference

| Option | Type / Format | Default | Description |
| :--- | :--- | :--- | :--- |
| `higher_is_better` | `bool` | `true` | Determines ranking order. If `true`, highest value is rank 1; if `false`, lowest value is rank 1. |
| `bold` | `int`, `list[int]`, `bool` | `[]` | Rank(s) to bold. `1` = best, `-1` = worst, `[1, 2]` = top 2, `true` = rank 1. |
| `underline` | `int`, `list[int]`, `bool` | `[]` | Rank(s) to underline. `2` = 2nd best, `-1` = worst, etc. |
| `italic` | `int`, `list[int]`, `bool` | `[]` | Rank(s) to italicize. `3` = 3rd best, `-1` = worst, `-2` = 2nd worst, etc. |
| `decimals` | `int` | `None` | Number of decimal places to display (e.g., `2` yields `0.88`). |
| `si_prefix` / `auto_scale` | `bool` or `str` | `None` | Automatically scales large/small numbers with SI prefixes. `true`/`"si"`/`"decimal"` uses base-1000 (`k`, `M`, `G`, `µ`, etc.); `"binary"`/`"iec"` uses base-1024 (`Ki`, `Mi`, `Gi`). |
| `scale` | `float` | `None` | Multiplier applied to values before formatting (e.g., `100` converts `0.85` to `85.0`). |
| `unit` | `str` | `None` | Unit suffix appended after the number and any uncertainty (e.g. `dB`, `ms`, `%`). |
| `color` | `str` or `dict[int, str]` | `None` | Text color. Can be a static color name/hex (e.g. `"blue"`, `"#336699"`) or a rank dictionary (e.g. `{1: "ForestGreen", -1: "red"}`). |
| `cell_color` | `str` or `dict[int, str]` | `None` | Cell background color using LaTeX `\cellcolor`. Can be a static color name/hex or a rank dictionary (e.g. `{1: "green!15", -1: "red!15"}`). |
| `cell_color_<N>` | `str` | `None` | Shortcut to assign background color for rank `N` (e.g. `cell_color_1: "green!15"`). |
| `styles` | `list[str]` or `str` | `[]` | Static styles applied unconditionally to all cells in the group (e.g., `["italic"]`). |
| `custom_format` | `str` | `None` | Custom Python format string (e.g., `"{:.2f}%"`). |
| `align_numbers` | `bool` | `true` | Automatically aligns decimal points, minus signs, and plus-minus (`\pm`) signs in columns without shifting. Set `false` to opt out. |

#### Rank Indexing & Direction

- **Positive integers (`1, 2, 3, ...`)**: Count from the **best** model (1 = best, 2 = second best, etc.).
- **Negative integers (`-1, -2, -3, ...`)**: Count from the **worst** model (-1 = worst, -2 = second worst, etc.).
- **Ties**: If multiple models share the same rounded value, all tied models receive the assigned style/color.
- **Direction**:
  - When `higher_is_better: true`: Highest value is rank `1`, lowest is rank `-1`.
  - When `higher_is_better: false`: Lowest value is rank `1` (e.g. lowest latency), highest is rank `-1` (worst latency).

---

## Command-Line Interface (CLI)

```bash
# Generate LaTeX with rules
latex-table-generator metrics.csv template.txt -r rules.yaml -o table.tex --align

# Generate and compile directly to PDF and PNG preview
latex-table-generator metrics.csv template.txt -r rules.yaml --pdf table.pdf --png table.png
```

---

## Development & Testing

### Running Tests
```bash
uv run pytest
```

### Pre-commit & Code Quality
This project uses **pre-commit** with **ruff** formatting, linting, and automated test execution before every commit:

```bash
# Install git hooks
uv run pre-commit install

# Run all hooks manually
uv run pre-commit run --all-files
```
