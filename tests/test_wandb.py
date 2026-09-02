"""Tests for Weights & Biases (WandB) metrics loader and CSV exporter."""

import csv
import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

import pytest
from latex_table_generator.wandb_loader import fetch_wandb_metrics

load_dotenv()


class MockWandbRun:
    def __init__(
        self, run_id: str, name: str, summary: dict, config: dict | None = None
    ):
        self.id = run_id
        self.name = name
        self.summary = summary
        self.config = config or {}


@pytest.fixture
def mock_wandb_api():
    mock_api = MagicMock()
    run1 = MockWandbRun("run_001", "snr loss", {"test_loss": 0.42, "accuracy": 0.88})
    run2 = MockWandbRun(
        "run_002", "drifting loss", {"test_loss": 0.15, "accuracy": 0.94}
    )

    mock_project = MagicMock()
    mock_project.name = "my_project"
    mock_api.projects.return_value = [mock_project]

    def mock_run(path: str):
        if "run_001" in path:
            return run1
        elif "run_002" in path:
            return run2
        raise ValueError(f"Run {path} not found")

    mock_api.run.side_effect = mock_run
    return mock_api


def test_fetch_wandb_metrics_default_names(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            run_ids=["run_001", "run_002"],
            metrics=["test_loss"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2

    assert reader[0]["model"] == "snr loss"
    assert reader[0]["id"] == "run_001"
    assert float(reader[0]["test_loss"]) == 0.42

    assert reader[1]["model"] == "drifting loss"
    assert reader[1]["id"] == "run_002"
    assert float(reader[1]["test_loss"]) == 0.15


def test_fetch_wandb_metrics_custom_run_names(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            run_ids=["run_001", "run_002"],
            run_names=["CustomModelA", "CustomModelB"],
            metrics=["test_loss"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert reader[0]["model"] == "CustomModelA"
    assert reader[1]["model"] == "CustomModelB"


def test_fetch_wandb_metrics_alternative_metric_names(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            run_ids=["run_001", "run_002"],
            metrics=["test_loss", "accuracy"],
            metric_names=["loss", "acc"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert "loss" in reader[0]
    assert "acc" in reader[0]
    assert float(reader[0]["loss"]) == 0.42
    assert float(reader[0]["acc"]) == 0.88


def test_fetch_wandb_metrics_file_output(mock_wandb_api, tmp_path: Path):
    out_file = tmp_path / "wandb_out.csv"
    with patch("wandb.Api", return_value=mock_wandb_api):
        fetch_wandb_metrics(
            run_ids=["run_001", "run_002"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "snr loss,run_001,0.42" in content


@pytest.mark.skipif(
    not os.getenv("WANDB_API_KEY"),
    reason="Live WandB API key not available in environment",
)
def test_live_wandb_fetch():
    csv_out = fetch_wandb_metrics(
        run_ids=["300826143817", "300826145103"],
        metrics=["test_loss"],
    )
    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2
    assert reader[0]["id"] == "300826143817"
    assert reader[1]["id"] == "300826145103"
    assert "test_loss" in reader[0]
