"""WandB integration for fetching run metrics, caching, and saving them to CSV files."""

from __future__ import annotations

import csv
import fnmatch
import io
import json
import os
import warnings
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tqdm.auto import tqdm


def _find_matching_metrics(pattern: str, candidate_keys: Iterable[str]) -> list[str]:
    """Find metric keys matching pattern using fnmatch or substring fallback."""
    candidates = list(candidate_keys)
    has_wildcard = any(c in pattern for c in ("*", "?", "["))
    if has_wildcard:
        return sorted([k for k in candidates if fnmatch.fnmatch(k, pattern)])

    # No wildcards: check exact match first
    if pattern in candidates:
        return [pattern]

    # Fallback to substring matching
    return sorted([k for k in candidates if pattern in k])


def _to_json_safe_dict(d: Any) -> dict[str, Any]:
    """Convert a dictionary or dict-like object to JSON-safe primitives."""
    if not d:
        return {}
    if hasattr(d, "_json_dict") and isinstance(d._json_dict, dict):
        d = d._json_dict
    elif not isinstance(d, dict):
        try:
            d = dict(d)
        except Exception:
            return {}

    safe: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool, type(None))):
            safe[str(k)] = v
        elif hasattr(v, "item"):
            try:
                safe[str(k)] = v.item()
            except Exception:
                safe[str(k)] = str(v)
        elif isinstance(v, (list, tuple)):
            safe[str(k)] = [
                x if isinstance(x, (int, float, str, bool, type(None))) else str(x)
                for x in v
            ]
        elif isinstance(v, dict):
            safe[str(k)] = _to_json_safe_dict(v)
        else:
            safe[str(k)] = str(v)
    return safe


def _get_cache_file(cache_dir: Path, run_id: str) -> Path:
    """Return the cache file path for a run ID."""
    sanitized_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_id)
    return cache_dir / f"{sanitized_id}.json"


def _read_cached_run(
    cache_dir: Path,
    run_id: str,
    metrics: Sequence[str],
) -> dict[str, Any] | None:
    """Read cached run data if available and contains all requested metrics."""
    cache_file = _get_cache_file(cache_dir, run_id)
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None

        summary = data.get("summary", {})
        config = data.get("config", {})
        available_keys = set(summary.keys()) | set(config.keys())

        # Check if all requested metric patterns match available keys in cache
        for m in metrics:
            matches = _find_matching_metrics(m, available_keys)
            if len(matches) > 1:
                error_msg = f"Multiple metrics matched pattern '{m}': {matches}"
                print(error_msg)
                raise ValueError(error_msg)
            if len(matches) == 0:
                return None

        return data
    except ValueError:
        raise
    except Exception:
        return None


def _write_cached_run(
    cache_dir: Path,
    run_id: str,
    name: str,
    summary: Mapping[str, Any] | None,
    config: Mapping[str, Any] | None,
    entity: str | None = None,
    project: str | None = None,
) -> None:
    """Write run metadata and metrics to local JSON cache."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = _get_cache_file(cache_dir, run_id)

        data = {
            "id": run_id,
            "name": name,
            "entity": entity,
            "project": project,
            "summary": _to_json_safe_dict(summary),
            "config": _to_json_safe_dict(config),
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


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
    show_progress: bool = True,
    use_cache: bool = True,
    cache_dir: str | Path = ".wandb_cache",
    force_refresh: bool = False,
    max_runs: int | None = None,
) -> str:
    """Fetch metrics from Weights & Biases (WandB) runs, cache them locally, and save to CSV.

    Parameters
    ----------
    metrics : sequence of str
        Sequence of metric keys or patterns to extract from run summaries/configs
        (e.g. ['test_loss'], ['*loss*'], or ['train*loss']).
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
    show_progress : bool, default True
        Whether to show a tqdm progress bar while loading runs (disappears when done).
    use_cache : bool, default True
        Whether to cache run metrics to local disk to avoid repeated network calls.
    cache_dir : str or Path, default '.wandb_cache'
        Directory where cached run JSON files will be stored.
    force_refresh : bool, default False
        If True, ignores local cache and re-fetches fresh data from WandB.
    max_runs : int | None, optional
        Maximum number of runs to fetch from the project.

    Returns
    -------
    str
        The generated CSV content as a string.
    """
    import wandb

    effective_run_ids = run_ids
    effective_project = project

    if metrics is None or isinstance(metrics, str) or not isinstance(metrics, Sequence):
        raise ValueError(
            "The 'metrics' argument must be provided as a sequence of metric names or patterns."
        )

    if len(metrics) == 0:
        raise ValueError(
            "The 'metrics' argument must contain at least one metric name or pattern."
        )

    if not all(isinstance(m, str) for m in metrics):
        raise ValueError("All elements in 'metrics' must be strings.")

    cache_dir_path = Path(cache_dir)

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

    api: wandb.Api | None = None

    def _get_api() -> wandb.Api:
        nonlocal api
        if api is None:
            if effective_api_key:
                api = wandb.Api(api_key=effective_api_key)
            else:
                api = wandb.Api()
        return api

    # 3. Resolve column headers for metrics
    col_headers: list[str] = []
    if metric_names and len(metric_names) > 0:
        for i, m in enumerate(metrics):
            if i < len(metric_names) and metric_names[i]:
                col_headers.append(str(metric_names[i]).strip())
            else:
                col_headers.append(str(m).strip())
    else:
        col_headers = [str(m).strip() for m in metrics]

    # 4. Fetch runs data
    extracted_runs: list[dict[str, Any]] = []

    # Case A: project is given and run_ids is omitted -> fetch all runs from project
    if (effective_run_ids is None or len(effective_run_ids) == 0) and effective_project:
        project_path = (
            f"{effective_entity}/{effective_project}"
            if effective_entity
            else effective_project
        )
        api_inst = _get_api()
        runs_query = api_inst.runs(project_path)
        raw_runs = list(runs_query)

        if max_runs is not None and max_runs > 0:
            raw_runs = raw_runs[:max_runs]

        if len(raw_runs) > warn_threshold:
            warnings.warn(
                f"WandB project '{effective_project}' contains {len(raw_runs)} runs "
                f"(warning threshold is {warn_threshold}). "
                f"Fetching metrics for a large number of runs may take longer.",
                UserWarning,
                stacklevel=2,
            )

        progress_bar = tqdm(
            raw_runs,
            desc=f"Loading WandB runs ({effective_project})",
            leave=False,
            disable=not show_progress,
        )

        for run_obj in progress_bar:
            run_id_str = str(run_obj.id).strip()
            name_str = str(run_obj.name).strip() if run_obj.name else run_id_str

            summary_dict = (
                run_obj.summary._json_dict
                if hasattr(run_obj.summary, "_json_dict")
                else (dict(run_obj.summary) if hasattr(run_obj, "summary") else {})
            )
            config_dict = dict(run_obj.config) if hasattr(run_obj, "config") else {}

            if use_cache:
                _write_cached_run(
                    cache_dir=cache_dir_path,
                    run_id=run_id_str,
                    name=name_str,
                    summary=summary_dict,
                    config=config_dict,
                    entity=effective_entity,
                    project=effective_project,
                )

            extracted_runs.append(
                {
                    "id": run_id_str,
                    "name": name_str,
                    "summary": summary_dict,
                    "config": config_dict,
                }
            )

    # Case B: explicit run_ids provided
    elif effective_run_ids:
        cached_projects: list[str] = []
        if effective_project:
            cached_projects = [effective_project]
        last_successful_project: str | None = effective_project

        progress_bar = tqdm(
            effective_run_ids,
            desc="Loading WandB runs",
            leave=False,
            disable=not show_progress,
        )

        for run_id_raw in progress_bar:
            run_id_str = str(run_id_raw).strip()

            # Check local cache first if enabled and not force_refresh
            cached_data = None
            if use_cache and not force_refresh:
                cached_data = _read_cached_run(cache_dir_path, run_id_str, metrics)

            if cached_data is not None:
                extracted_runs.append(cached_data)
                continue

            # Not cached or refresh requested -> reach out to WandB API
            api_inst = _get_api()
            found_run = None

            if "/" in run_id_str:
                try:
                    found_run = api_inst.run(run_id_str)
                except Exception:
                    pass

            if not found_run and last_successful_project and effective_entity:
                try:
                    found_run = api_inst.run(
                        f"{effective_entity}/{last_successful_project}/{run_id_str}"
                    )
                except Exception:
                    pass

            if not found_run and effective_entity:
                if not cached_projects:
                    try:
                        cached_projects = [
                            p.name for p in api_inst.projects(effective_entity)
                        ]
                    except Exception:
                        cached_projects = []

                for proj in cached_projects:
                    if proj == last_successful_project:
                        continue
                    try:
                        found_run = api_inst.run(
                            f"{effective_entity}/{proj}/{run_id_str}"
                        )
                        last_successful_project = proj
                        break
                    except Exception:
                        continue

            if not found_run:
                raise ValueError(
                    f"WandB run '{run_id_str}' not found in entity '{effective_entity}' "
                    f"(checked projects: {cached_projects})."
                )

            name_str = str(found_run.name).strip() if found_run.name else run_id_str
            summary_dict = (
                found_run.summary._json_dict
                if hasattr(found_run.summary, "_json_dict")
                else (dict(found_run.summary) if hasattr(found_run, "summary") else {})
            )
            config_dict = dict(found_run.config) if hasattr(found_run, "config") else {}

            if use_cache:
                _write_cached_run(
                    cache_dir=cache_dir_path,
                    run_id=run_id_str,
                    name=name_str,
                    summary=summary_dict,
                    config=config_dict,
                    entity=effective_entity,
                    project=last_successful_project,
                )

            extracted_runs.append(
                {
                    "id": run_id_str,
                    "name": name_str,
                    "summary": summary_dict,
                    "config": config_dict,
                }
            )

    else:
        raise ValueError(
            "Either 'project' (to fetch all project runs) or 'run_ids' (to fetch specific runs) must be provided."
        )

    # 5. Extract rows for each run
    rows_data: list[dict[str, Any]] = []

    for idx, run_info in enumerate(extracted_runs):
        run_id_str = run_info["id"]

        # Determine model name
        if run_names and idx < len(run_names) and run_names[idx]:
            model_name = str(run_names[idx]).strip()
        else:
            model_name = str(run_info.get("name") or run_id_str)

        row_dict: dict[str, Any] = {
            model_column: model_name,
            id_column: run_id_str,
        }

        summary = run_info.get("summary", {})
        config = run_info.get("config", {})
        run_keys = set(summary.keys()) | set(config.keys())

        for pat, target_col in zip(metrics, col_headers):
            matches = _find_matching_metrics(pat, run_keys)
            if len(matches) > 1:
                error_msg = (
                    f"Multiple metrics matched pattern '{pat}' for run '{run_id_str}' "
                    f"({model_name}): {matches}"
                )
                print(error_msg)
                raise ValueError(error_msg)
            if len(matches) == 0:
                error_msg = (
                    f"No metric found matching pattern '{pat}' for run '{run_id_str}' "
                    f"({model_name}). Available metrics: {sorted(run_keys)}"
                )
                print(error_msg)
                raise ValueError(error_msg)

            matched_key = matches[0]
            val: Any = None
            if matched_key in summary:
                val = summary[matched_key]
            elif matched_key in config:
                val = config[matched_key]

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
