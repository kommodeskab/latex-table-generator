"""Tests for MetricsStore and load_metrics."""

from pathlib import Path
import pytest
from latex_table_generator.metrics import (
    MetricNotFoundError,
    MetricsStore,
    load_metrics,
)


def test_metrics_store_from_dict():
    data = {
        "ModelA": {"acc": 0.8523, "f1": 0.8411},
        "ModelB": {"acc": 0.9123, "f1": 0.9045},
    }
    store = MetricsStore(data)
    assert store.rows == ["ModelA", "ModelB"]
    assert store.columns == ["acc", "f1"]
    assert store.get("ModelA", "acc") == 0.8523
    assert store.get("ModelB", "f1") == 0.9045
    assert store["ModelA", "acc"] == 0.8523
    assert ("ModelA", "acc") in store
    assert "ModelA" in store


def test_metrics_store_from_csv_string():
    csv_content = """model,Accuracy,Precision,Recall,F1
ModelA,0.8523,0.8411,0.8634,0.8521
ModelB,0.9123,0.9045,0.9201,0.9122
"""
    store = MetricsStore.from_csv(csv_content)
    assert store.rows == ["ModelA", "ModelB"]
    assert "Accuracy" in store.columns
    assert "F1" in store.columns
    assert store.get("ModelA", "Accuracy") == 0.8523
    assert store.get("ModelB", "Precision") == 0.9045


def test_metrics_store_from_csv_file(tmp_path: Path):
    csv_file = tmp_path / "metrics.csv"
    csv_file.write_text(
        ",Accuracy,F1\nModel 1,0.75,0.72\nModel 2,0.88,0.86\n", encoding="utf-8"
    )

    store = load_metrics(csv_file)
    assert store.rows == ["Model 1", "Model 2"]
    assert store.columns == ["Accuracy", "F1"]
    assert store.get("Model 1", "Accuracy") == 0.75
    assert store.get("Model 2", "F1") == 0.86


def test_metrics_store_whitespace_and_percentages():
    csv_content = """  model  ,  Acc  ,  Rate
  ResNet-50  ,  0.8912  ,  95.5%
"""
    store = MetricsStore.from_csv(csv_content)
    assert store.rows == ["ResNet-50"]
    assert store.columns == ["Acc", "Rate"]
    assert store.get("ResNet-50", "Acc") == 0.8912
    assert store.get("ResNet-50", "Rate") == 0.955


def test_metrics_store_not_found_error():
    store = MetricsStore({"ModelA": {"acc": 0.85}})
    with pytest.raises(MetricNotFoundError) as exc_info:
        store.get("ModelB", "acc")
    assert "Row 'ModelB' not found" in str(exc_info.value)

    with pytest.raises(MetricNotFoundError) as exc_info:
        store.get("ModelA", "recall")
    assert "Column 'recall' not found" in str(exc_info.value)


def test_metrics_store_default_value():
    store = MetricsStore({"ModelA": {"acc": 0.85}})
    assert store.get("ModelA", "recall", default=0.0) == 0.0
    assert store.get("ModelX", "acc", default=None) is None
