"""WandB integration for fetching run metrics and saving them to CSV files."""

from __future__ import annotations

import csv
import io
import os
import warnings
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv


def fetch_wandb_metrics(
    metrics: Sequence[str] | None = None,
    run_ids: Sequence[str] | None = None,
    project: str | None = None,
    output_path: str | Path | None = None,
    run_names: Sequence[str] | None = None,
    metric_names: Sequence[str] | None = None,
    entity: str | None = None,
    api_key: str | None = None,
    env_file: str | Path | None = ".env",
    id_column: str = "id",
    model_column: str = "model",
    warn_threshold: int = 50,
    **kwargs: Any,
) -> str:
    """Fetch metrics from Weights & Biases (WandB) runs and save them to a CSV file.

    Parameters
    ----------
    metrics : list of str
        List of metric keys to extract from run summaries/configs (e.g. ['test_loss']).
    run_ids : list of str, optional
        List of WandB run IDs. If omitted/None and `project` is given, all runs in `project` are fetched.
    project : str, optional
        WandB project name. If `run_ids` is omitted, all runs in this project will be exported.
    output_path : str or Path, optional
        Path where the generated .csv file will be saved.
    run_names : list of str, optional
        Custom model/row names. If None or empty, uses the run names from WandB.
    metric_names : list of str, optional
        Alternative column names for the metrics in the CSV. If None or empty, uses `metrics`.
    entity : str, optional
        WandB entity (team or user). Defaults to `WANDB_ENTITY` from environment/.env.
    api_key : str, optional
        WandB API key. Defaults to `WANDB_API_KEY` from environment/.env.
    env_file : str or Path, optional
        Path to .env file to load environment variables from (default: '.env').
    id_column : str, default 'id'
        Name of the column storing run IDs in the CSV.
    model_column : str, default 'model'
        Name of the column storing model/run names in the CSV.
    warn_threshold : int, default 50
        Threshold for number of runs before raising a warning about long fetch times.

    Returns
    -------
    str
        The generated CSV content as a string.

    Examples
    --------
    >>> # Fetch all runs from a project:
    >>> csv_content = fetch_wandb_metrics(
    ...     project="denoising_test",
    ...     metrics=["test_loss"],
    ...     output_path="wandb_metrics.csv",
    ... )
    >>> # Fetch specific run IDs:
    >>> csv_content = fetch_wandb_metrics(
    ...     run_ids=["300826143817", "300826145103"],
    ...     metrics=["test_loss"],
    ...     output_path="wandb_metrics.csv",
    ... )
    """
    import wandb

    # Support backwards compatibility if run_ids and metrics are passed positionally
    effective_run_ids = run_ids
    effective_metrics = metrics
    effective_project = project

    # Handle positional variations or kwargs
    if effective_metrics is None and "metrics" in kwargs:
        effective_metrics = kwargs["metrics"]

    if (
        effective_run_ids is None
        and isinstance(metrics, Sequence)
        and not isinstance(metrics, str)
    ):
        # Check if first positional argument was actually run_ids and second was metrics
        if "metrics" in kwargs:
            effective_run_ids = metrics
            effective_metrics = kwargs["metrics"]

    if effective_metrics is None:
        raise ValueError(
            "The 'metrics' argument must be provided as a list of metric names."
        )

    # 1. Load environment variables from .env if present
    if env_file:
        env_path = Path(env_file)
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
    else:
        load_dotenv()

    # 2. Resolve credentials
    effective_api_key = api_key or os.getenv("WANDB_API_KEY")
    effective_entity = entity or os.getenv("WANDB_ENTITY")

    if effective_api_key:
        api = wandb.Api(api_key=effective_api_key)
    else:
        api = wandb.Api()

    # 3. Resolve column headers for metrics
    col_headers: list[str] = []
    if metric_names and len(metric_names) > 0:
        for i, m in enumerate(effective_metrics):
            if i < len(metric_names) and metric_names[i]:
                col_headers.append(str(metric_names[i]).strip())
            else:
                col_headers.append(str(m).strip())
    else:
        col_headers = [str(m).strip() for m in effective_metrics]

    # 4. Fetch runs
    run_objects: list[Any] = []

    # Case A: project is given and run_ids is omitted -> fetch all runs from project
    if (effective_run_ids is None or len(effective_run_ids) == 0) and effective_project:
        project_path = (
            f"{effective_entity}/{effective_project}"
            if effective_entity
            else effective_project
        )
        runs_query = api.runs(project_path)
        run_objects = list(runs_query)

        if len(run_objects) > warn_threshold:
            warnings.warn(
                f"WandB project '{effective_project}' contains {len(run_objects)} runs "
                f"(warning threshold is {warn_threshold}). "
                f"Fetching metrics for a large number of runs may take longer.",
                UserWarning,
                stacklevel=2,
            )

    # Case B: explicit run_ids provided
    elif effective_run_ids:
        # Cache available projects if needed
        cached_projects: list[str] = []
        if effective_project:
            cached_projects = [effective_project]
        elif effective_entity:
            try:
                cached_projects = [p.name for p in api.projects(effective_entity)]
            except Exception:
                cached_projects = []

        last_successful_project: str | None = effective_project

        for run_id_raw in effective_run_ids:
            run_id_str = str(run_id_raw).strip()
            found_run = None

            # Try direct path if run_id contains slashes
            if "/" in run_id_str:
                try:
                    found_run = api.run(run_id_str)
                except Exception:
                    pass

            # Try last successful project
            if not found_run and last_successful_project and effective_entity:
                try:
                    found_run = api.run(
                        f"{effective_entity}/{last_successful_project}/{run_id_str}"
                    )
                except Exception:
                    pass

            # Search across projects
            if not found_run and effective_entity:
                for proj in cached_projects:
                    if proj == last_successful_project:
                        continue
                    try:
                        found_run = api.run(f"{effective_entity}/{proj}/{run_id_str}")
                        last_successful_project = proj
                        break
                    except Exception:
                        continue

            if not found_run:
                raise ValueError(
                    f"WandB run '{run_id_str}' not found in entity '{effective_entity}' "
                    f"(checked projects: {cached_projects})."
                )

            run_objects.append(found_run)

    else:
        raise ValueError(
            "Either 'project' (to fetch all project runs) or 'run_ids' (to fetch specific runs) must be provided."
        )

    # 5. Extract rows for each run
    rows_data: list[dict[str, Any]] = []

    for idx, run_obj in enumerate(run_objects):
        run_id_str = str(run_obj.id).strip()

        # Determine model name
        if run_names and idx < len(run_names) and run_names[idx]:
            model_name = str(run_names[idx]).strip()
        else:
            model_name = str(run_obj.name).strip() if run_obj.name else run_id_str

        # Extract metric values
        row_dict: dict[str, Any] = {
            model_column: model_name,
            id_column: run_id_str,
        }

        for orig_metric, target_col in zip(effective_metrics, col_headers):
            val: Any = None
            if hasattr(run_obj, "summary") and orig_metric in run_obj.summary:
                val = run_obj.summary[orig_metric]
            elif hasattr(run_obj, "config") and orig_metric in run_obj.config:
                val = run_obj.config[orig_metric]
            elif hasattr(run_obj, "summary") and hasattr(run_obj.summary, "_json_dict"):
                val = run_obj.summary._json_dict.get(orig_metric)

            # Convert numpy / torch tensors or NaN if needed
            if hasattr(val, "item"):
                val = val.item()

            row_dict[target_col] = val if val is not None else float("nan")

        rows_data.append(row_dict)

    # 6. Generate CSV string
    fieldnames = [model_column, id_column, *col_headers]
    output_io = io.StringIO()
    writer = csv.DictWriter(output_io, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows_data)

    csv_content = output_io.getvalue()

    # 7. Write to output file if provided
    if output_path is not None:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(csv_content, encoding="utf-8")

    return csv_content


# Alias for convenience
load_wandb_metrics = fetch_wandb_metrics
export_wandb_metrics = fetch_wandb_metrics
