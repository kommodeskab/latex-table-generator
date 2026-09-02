"""Tests for CLI interface."""

from pathlib import Path
from latex_table_generator.cli import main


def test_cli_basic(tmp_path: Path, capsys):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text("model,acc\nModelA,0.8523\n", encoding="utf-8")

    template_file = tmp_path / "template.txt"
    template_file.write_text("Model A & {ModelA.acc} \\\\", encoding="utf-8")

    exit_code = main([str(csv_file), str(template_file), "-d", "2"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Model A & 0.85 \\\\" in captured.out


def test_cli_output_file(tmp_path: Path, capsys):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text("model,acc\nModelA,0.8523\n", encoding="utf-8")

    template_file = tmp_path / "template.txt"
    template_file.write_text("Model A & {ModelA.acc} \\\\", encoding="utf-8")

    out_file = tmp_path / "table.tex"

    exit_code = main(
        [str(csv_file), str(template_file), "-d", "2", "-o", str(out_file)]
    )
    assert exit_code == 0
    assert out_file.exists()
    assert "Model A & 0.85 \\\\" in out_file.read_text(encoding="utf-8")
