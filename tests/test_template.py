"""Tests for template rendering and alignment."""

import pytest
from latex_table_generator.metrics import MetricNotFoundError, MetricsStore
from latex_table_generator.template import TemplateRenderer, align_latex_table


@pytest.fixture
def sample_metrics():
    return MetricsStore(
        {
            "ModelA": {"acc_mean": 0.8523, "acc_std": 0.0123, "f1": 0.8411},
            "ModelB": {"acc_mean": 0.9123, "acc_std": 0.0095, "f1": 0.9045},
        }
    )


def test_render_single_placeholders(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)
    template = "Model A & {ModelA.f1} \\\\\nModel B & {ModelB.f1} \\\\"
    result = renderer.render(template)
    expected = "Model A & 0.84 \\\\\nModel B & 0.90 \\\\"
    assert result == expected


def test_render_uncertainty_placeholders(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)
    template = "Model A & {ModelA.acc_mean +- ModelA.acc_std} \\\\"
    result = renderer.render(template)
    assert result == r"Model A & 0.85 \ensuremath{\pm} 0.01 \\"


def test_render_various_pm_operators(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)
    t1 = "{ModelA.acc_mean +- ModelA.acc_std}"
    t2 = "{ModelA.acc_mean +/- ModelA.acc_std}"
    t3 = r"{ModelA.acc_mean \pm ModelA.acc_std}"
    t4 = "{ModelA.acc_mean ± ModelA.acc_std}"

    for t in (t1, t2, t3, t4):
        assert renderer.render(t) == r"0.85 \ensuremath{\pm} 0.01"


def test_render_custom_spec_and_styling(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)

    # Specific format spec overrides global decimals
    t1 = "{ModelA.acc_mean +- ModelA.acc_std : .3f}"
    assert renderer.render(t1) == r"0.852 \ensuremath{\pm} 0.012"

    # Bold styling
    t2 = "{ModelA.f1 : bold}"
    assert renderer.render(t2) == r"\textbf{0.84}"

    # Nested LaTeX command
    t3 = r"\textbf{{ModelA.f1}}"
    assert renderer.render(t3) == r"\textbf{0.84}"


def test_render_preserves_regular_latex(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)
    template = r"""\begin{tabular}{lcc}
\toprule
Method & Accuracy & F1-Score \\
\midrule
Model A & {ModelA.acc_mean +- ModelA.acc_std} & {ModelA.f1} \\
\bottomrule
\end{tabular}"""
    result = renderer.render(template)
    expected = r"""\begin{tabular}{lcc}
\toprule
Method & Accuracy & F1-Score \\
\midrule
Model A & 0.85 \ensuremath{\pm} 0.01 & 0.84 \\
\bottomrule
\end{tabular}"""
    assert result == expected


def test_render_missing_metric_raises_error(sample_metrics):
    renderer = TemplateRenderer(sample_metrics, decimals=2)
    template = "Model C & {ModelC.f1} \\\\"
    with pytest.raises(MetricNotFoundError):
        renderer.render(template)


def test_align_latex_table():
    unaligned = r"""\begin{tabular}{lcc}
\toprule
Model & Accuracy & F1 \\
\midrule
Model A & 0.85 \pm 0.01 & 0.84 \\
Model B (Extended) & 0.91 \pm 0.01 & 0.90 \\
\bottomrule
\end{tabular}"""

    aligned = align_latex_table(unaligned)
    assert "Model A            & 0.85 \\pm 0.01 & 0.84 \\\\" in aligned
    assert "Model B (Extended) & 0.91 \\pm 0.01 & 0.90 \\\\" in aligned


def test_caption_with_period_ignored():
    metrics = MetricsStore({"ModelA": {"acc": 0.9}})
    renderer = TemplateRenderer(metrics, decimals=2)
    template = (
        r"\caption{Results on dataset. Benchmark.} \label{tab.1} Model: {ModelA.acc}"
    )
    result = renderer.render(template)
    assert (
        result == r"\caption{Results on dataset. Benchmark.} \label{tab.1} Model: 0.90"
    )


def test_row_with_dot():
    metrics = MetricsStore({"GPT-3.5": {"acc": 0.892}})
    renderer = TemplateRenderer(metrics, decimals=2)
    template = "GPT-3.5: {GPT-3.5.acc}"
    result = renderer.render(template)
    assert result == "GPT-3.5: 0.89"


def test_quoted_row_name():
    metrics = MetricsStore({"Model 1.0": {"acc": 0.892}})
    renderer = TemplateRenderer(metrics, decimals=2)
    template = "Model: {'Model 1.0'.acc}"
    result = renderer.render(template)
    assert result == "Model: 0.89"


def test_align_latex_table_with_percent_signs():
    from latex_table_generator.template import align_latex_table

    table = (
        "\\textbf{Model} & \\textbf{Acc (\\%)} & \\textbf{Latency} \\\\ % header comment\n"
        "ModelA & 85.2\\% & 10.5 ms \\\\\n"
        "ModelB & 90.1\\% & 8.2 ms \\\\ % best model\n"
    )
    aligned = align_latex_table(table)
    # Ensure escaped \% does not get treated as a comment delimiter
    assert r"\textbf{Acc (\%)}" in aligned
    assert r"85.2\%" in aligned
    assert r"90.1\%" in aligned
    # Ensure true comments remain at the end of rows
    assert "% header comment" in aligned
    assert "% best model" in aligned
