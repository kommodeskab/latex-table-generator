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
    mock_api.runs.return_value = [run1, run2]
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


def test_fetch_wandb_metrics_by_project(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            project="my_project",
            metrics=["test_loss"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2
    assert reader[0]["id"] == "run_001"
    assert reader[1]["id"] == "run_002"


def test_fetch_wandb_metrics_warn_threshold(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        with pytest.warns(UserWarning, match="contains 2 runs"):
            fetch_wandb_metrics(
                project="my_project",
                metrics=["test_loss"],
                entity="test_entity",
                warn_threshold=1,
            )


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


def test_fetch_wandb_metrics_overwrite_file_default(mock_wandb_api, tmp_path: Path):
    out_file = tmp_path / "wandb_out.csv"
    with patch("wandb.Api", return_value=mock_wandb_api):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )
        assert "snr loss" in out_file.read_text(encoding="utf-8")

        # By default overwrite_file=True, wipes and replaces existing file
        csv_out = fetch_wandb_metrics(
            run_ids=["run_002"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )

    content = out_file.read_text(encoding="utf-8")
    assert "snr loss" not in content
    assert "drifting loss" in content
    assert "drifting loss" in csv_out


def test_fetch_wandb_metrics_append_new_rows(mock_wandb_api, tmp_path: Path):
    out_file = tmp_path / "wandb_out.csv"
    with patch("wandb.Api", return_value=mock_wandb_api):
        # Initial write
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )

        # Append new row with overwrite_file=False
        csv_out = fetch_wandb_metrics(
            run_ids=["run_002"],
            metrics=["test_loss"],
            output_path=out_file,
            overwrite_file=False,
            entity="test_entity",
        )

    content = out_file.read_text(encoding="utf-8")
    reader = list(csv.DictReader(io.StringIO(content)))
    assert len(reader) == 2
    assert reader[0]["model"] == "snr loss"
    assert reader[0]["id"] == "run_001"
    assert reader[1]["model"] == "drifting loss"
    assert reader[1]["id"] == "run_002"

    returned_reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(returned_reader) == 2
    assert returned_reader[0]["model"] == "snr loss"
    assert returned_reader[1]["model"] == "drifting loss"


def test_fetch_wandb_metrics_append_duplicate_model_error(
    mock_wandb_api, tmp_path: Path
):
    out_file = tmp_path / "wandb_out.csv"
    with patch("wandb.Api", return_value=mock_wandb_api):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )

        with pytest.raises(ValueError) as exc_info:
            fetch_wandb_metrics(
                run_ids=["run_001"],
                metrics=["test_loss"],
                output_path=out_file,
                overwrite_file=False,
                entity="test_entity",
            )

        assert "Model 'snr loss' already exists" in str(exc_info.value)


def test_fetch_wandb_metrics_append_header_mismatch_error(
    mock_wandb_api, tmp_path: Path
):
    out_file = tmp_path / "wandb_out.csv"
    with patch("wandb.Api", return_value=mock_wandb_api):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            output_path=out_file,
            entity="test_entity",
        )

        with pytest.raises(ValueError) as exc_info:
            fetch_wandb_metrics(
                run_ids=["run_002"],
                metrics=["accuracy"],
                output_path=out_file,
                overwrite_file=False,
                entity="test_entity",
            )

        assert "CSV header mismatch" in str(exc_info.value)


def test_fetch_wandb_metrics_overwrite_file_invalid_type(mock_wandb_api):
    with pytest.raises(ValueError) as exc_info:
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            overwrite_file="false",  # type: ignore[arg-type]
        )
    assert "The 'overwrite_file' argument must be a boolean." in str(exc_info.value)


def test_fetch_wandb_metrics_caching(mock_wandb_api, tmp_path: Path):
    cache_dir = tmp_path / "custom_cache"
    with patch("wandb.Api", return_value=mock_wandb_api):
        # 1. First fetch: populates cache
        csv_1 = fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            cache_dir=cache_dir,
            use_cache=True,
            show_progress=False,
            entity="test_entity",
        )

    assert (cache_dir / "run_001.json").exists()

    # 2. Second fetch: should read from cache without calling mock_wandb_api.run again
    mock_wandb_api.run.reset_mock()
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_2 = fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            cache_dir=cache_dir,
            use_cache=True,
            show_progress=False,
            entity="test_entity",
        )

    mock_wandb_api.run.assert_not_called()
    assert csv_1 == csv_2


@pytest.mark.skipif(
    not os.getenv("WANDB_API_KEY"),
    reason="Live WandB API key not available in environment",
)
def test_live_wandb_fetch():
    try:
        csv_out = fetch_wandb_metrics(
            run_ids=["300826143817", "300826145103"],
            metrics=["test_loss"],
            show_progress=False,
        )
    except Exception as e:
        pytest.skip(f"WandB API service unavailable or timed out: {e}")

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2
    assert reader[0]["id"] == "300826143817"
    assert reader[1]["id"] == "300826145103"
    assert "test_loss" in reader[0]


@pytest.mark.skipif(
    not os.getenv("WANDB_API_KEY"),
    reason="Live WandB API key not available in environment",
)
def test_live_wandb_fetch_by_project():
    try:
        csv_out = fetch_wandb_metrics(
            project="denoising_test",
            metrics=["test_loss"],
            show_progress=False,
            max_runs=5,
        )
    except Exception as e:
        pytest.skip(f"WandB API service unavailable or timed out: {e}")

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) >= 2
    assert "id" in reader[0]
    assert "model" in reader[0]
    assert "test_loss" in reader[0]


def test_fetch_wandb_metrics_wildcard_patterns(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            run_ids=["run_001", "run_002"],
            metrics=["*loss*", "test*loss"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2
    assert "*loss*" in reader[0]
    assert "test*loss" in reader[0]
    assert float(reader[0]["*loss*"]) == 0.42
    assert float(reader[0]["test*loss"]) == 0.42
    assert float(reader[1]["*loss*"]) == 0.15
    assert float(reader[1]["test*loss"]) == 0.15


def test_fetch_wandb_metrics_substring_matching(mock_wandb_api):
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_out = fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["acc"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert "acc" in reader[0]
    assert float(reader[0]["acc"]) == 0.88


def test_fetch_wandb_metrics_duplicate_metrics_error():
    mock_api = MagicMock()
    run = MockWandbRun(
        "run_dup",
        "dup_model",
        {"train_loss": 0.5, "val_loss": 0.2, "accuracy": 0.9},
    )
    mock_api.run.return_value = run

    with patch("wandb.Api", return_value=mock_api):
        with pytest.raises(ValueError) as exc_info:
            fetch_wandb_metrics(
                project="my_project",
                run_ids=["run_dup"],
                metrics=["*loss*"],
                entity="test_entity",
            )
        err = str(exc_info.value)
        assert "Multiple metrics matched pattern '*loss*'" in err
        assert "train_loss" in err
        assert "val_loss" in err


def test_fetch_wandb_metrics_kwargs_disallowed(mock_wandb_api):
    with pytest.raises(TypeError):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["test_loss"],
            unexpected_arg="invalid",
        )


def test_fetch_wandb_metrics_metrics_type_validation(mock_wandb_api):
    with pytest.raises(ValueError, match="sequence of metric names or patterns"):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics="test_loss",  # string not allowed, must be sequence of strings
        )

    with pytest.raises(ValueError, match="at least one metric name or pattern"):
        fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=[],
        )


def test_fetch_wandb_metrics_patterns_with_caching(mock_wandb_api, tmp_path: Path):
    cache_dir = tmp_path / "pattern_cache"
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_1 = fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["*loss*"],
            cache_dir=cache_dir,
            use_cache=True,
            show_progress=False,
            entity="test_entity",
        )

    mock_wandb_api.run.reset_mock()
    with patch("wandb.Api", return_value=mock_wandb_api):
        csv_2 = fetch_wandb_metrics(
            run_ids=["run_001"],
            metrics=["*loss*"],
            cache_dir=cache_dir,
            use_cache=True,
            show_progress=False,
            entity="test_entity",
        )

    mock_wandb_api.run.assert_not_called()
    assert csv_1 == csv_2


def test_fetch_wandb_metrics_different_metric_names_per_run():
    mock_api = MagicMock()
    run1 = MockWandbRun("run_a", "Model A", {"train_loss": 0.42, "acc": 0.88})
    run2 = MockWandbRun("run_b", "Model B", {"val_loss": 0.15, "acc": 0.94})

    def mock_run(path: str):
        if "run_a" in path:
            return run1
        elif "run_b" in path:
            return run2
        raise ValueError("Not found")

    mock_api.run.side_effect = mock_run

    with patch("wandb.Api", return_value=mock_api):
        csv_out = fetch_wandb_metrics(
            project="my_project",
            run_ids=["run_a", "run_b"],
            metrics=["*loss*"],
            entity="test_entity",
        )

    reader = list(csv.DictReader(io.StringIO(csv_out)))
    assert len(reader) == 2
    assert float(reader[0]["*loss*"]) == 0.42
    assert float(reader[1]["*loss*"]) == 0.15


def test_fetch_wandb_metrics_missing_metric_error():
    mock_api = MagicMock()
    run = MockWandbRun("run_missing", "Model X", {"accuracy": 0.95})
    mock_api.run.return_value = run

    with patch("wandb.Api", return_value=mock_api):
        with pytest.raises(ValueError) as exc_info:
            fetch_wandb_metrics(
                project="my_project",
                run_ids=["run_missing"],
                metrics=["*loss*"],
                entity="test_entity",
            )
        err = str(exc_info.value)
        assert "No metric found matching pattern '*loss*'" in err
        assert "run_missing" in err
