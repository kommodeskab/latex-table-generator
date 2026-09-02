"""End-to-end tests for generate_latex_table and TableGenerator."""

from pathlib import Path
from latex_table_generator import TableGenerator, generate_latex_table, generate_table


def test_generate_latex_table_files(tmp_path: Path):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text(
        "model,acc_mean,acc_std,f1\n"
        "Baseline,0.8123,0.0245,0.8012\n"
        "Ours,0.9234,0.0102,0.9189\n",
        encoding="utf-8",
    )

    template_file = tmp_path / "template.txt"
    template_file.write_text(
        "\\begin{tabular}{lcc}\n"
        "Method & Accuracy & F1 \\\\\n"
        "\\hline\n"
        "Baseline & {Baseline.acc_mean +- Baseline.acc_std} & {Baseline.f1} \\\\\n"
        "Ours & {Ours.acc_mean +- Ours.acc_std} & {Ours.f1} \\\\\n"
        "\\end{tabular}\n",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.tex"

    result = generate_latex_table(
        csv_path=csv_file,
        template_path=template_file,
        decimals=2,
        output_path=output_file,
    )

    expected = (
        "\\begin{tabular}{lcc}\n"
        "Method & Accuracy & F1 \\\\\n"
        "\\hline\n"
        "Baseline & 0.81 \\ensuremath{\\pm} 0.02 & 0.80 \\\\\n"
        "Ours & 0.92 \\ensuremath{\\pm} 0.01 & 0.92 \\\\\n"
        "\\end{tabular}\n"
    )

    assert result == expected
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == expected


def test_table_generator_class(tmp_path: Path):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text(
        "model,val\nM1,12.3456\nM2,78.9012\n",
        encoding="utf-8",
    )

    generator = TableGenerator.from_csv(csv_file, decimals=1)
    res = generator.render("M1: {M1.val}, M2: {M2.val}")
    assert res == "M1: 12.3, M2: 78.9"


def test_generate_table_alias(tmp_path: Path):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text("model,score\nA,0.999\n", encoding="utf-8")

    res = generate_table(csv_file, "Score: {A.score}", decimals=2)
    assert res == "Score: 1.00"
