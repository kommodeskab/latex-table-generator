"""Metrics data loader and store for LaTeX table generation."""

from __future__ import annotations

import csv
import difflib
from pathlib import Path
from typing import Any, Mapping


class MetricNotFoundError(KeyError):
    """Raised when a requested metric (row, column) is not found in the MetricsStore."""

    def __init__(self, message: str, row: str | None = None, col: str | None = None):
        super().__init__(message)
        self.row = row
        self.col = col


class MetricsStore:
    """Stores 2D metrics data indexed by row name and column name."""

    def __init__(
        self,
        data: Mapping[str, Mapping[str, Any]] | None = None,
        rows: list[str] | None = None,
        columns: list[str] | None = None,
    ) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._rows: list[str] = []
        self._columns: list[str] = []

        if data is not None:
            for r_key, r_val in data.items():
                r_key_str = str(r_key).strip()
                self._data[r_key_str] = {}
                if r_key_str not in self._rows:
                    self._rows.append(r_key_str)
                for c_key, c_val in r_val.items():
                    c_key_str = str(c_key).strip()
                    self._data[r_key_str][c_key_str] = self._parse_val(c_val)
                    if c_key_str not in self._columns:
                        self._columns.append(c_key_str)

        if rows is not None:
            self._rows = [str(r).strip() for r in rows]
        if columns is not None:
            self._columns = [str(c).strip() for c in columns]

    @staticmethod
    def _parse_val(val: Any) -> Any:
        """Parse a cell value to float/int if possible, preserving NaN/strings."""
        if val is None:
            return float("nan")
        if isinstance(val, (int, float)):
            return val
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ("nan", "none", "null", "n/a", "-"):
            try:
                return float("nan")
            except ValueError:
                return val_str
        # Strip trailing % if present and parse as percentage
        if val_str.endswith("%"):
            try:
                return float(val_str[:-1].strip()) / 100.0
            except ValueError:
                pass
        try:
            return int(val_str)
        except ValueError:
            pass
        try:
            return float(val_str)
        except ValueError:
            return val_str

    @classmethod
    def from_csv(
        cls,
        csv_source: str | Path | Any,
        delimiter: str = ",",
        index_col: int | str = 0,
        strip_whitespace: bool = True,
        encoding: str = "utf-8",
    ) -> MetricsStore:
        """Load metrics from a CSV file path, string, or file-like object.

        Parameters
        ----------
        csv_source : str, Path, or file-like object
            File path to the CSV, CSV text content, or open file object.
        delimiter : str, default ","
            CSV delimiter.
        index_col : int or str, default 0
            The column index or column name to use as row keys.
        strip_whitespace : bool, default True
            Whether to strip leading/trailing whitespace from cell values and names.
        encoding : str, default "utf-8"
            File encoding if reading from a file path.

        Returns
        -------
        MetricsStore
        """
        # Determine whether csv_source is a file path or string content or file object
        if isinstance(csv_source, (str, Path)):
            path_obj = Path(csv_source)
            if path_obj.exists() and path_obj.is_file():
                with open(path_obj, "r", encoding=encoding) as f:
                    return cls._read_csv_fp(f, delimiter, index_col, strip_whitespace)
            elif isinstance(csv_source, str) and (
                "\n" in csv_source or delimiter in csv_source
            ):
                import io

                return cls._read_csv_fp(
                    io.StringIO(csv_source), delimiter, index_col, strip_whitespace
                )
            else:
                # File not found
                raise FileNotFoundError(f"CSV file not found: {csv_source}")
        elif hasattr(csv_source, "read"):
            return cls._read_csv_fp(csv_source, delimiter, index_col, strip_whitespace)
        elif hasattr(csv_source, "to_dict"):
            # Pandas DataFrame or Series
            return cls.from_dataframe(csv_source)
        else:
            raise TypeError(f"Unsupported CSV source type: {type(csv_source)}")

    @classmethod
    def from_dataframe(cls, df: Any) -> MetricsStore:
        """Convert a pandas DataFrame to a MetricsStore."""
        rows = [str(r).strip() for r in df.index]
        columns = [str(c).strip() for c in df.columns]
        data: dict[str, dict[str, Any]] = {}
        for r in df.index:
            r_str = str(r).strip()
            data[r_str] = {}
            for c in df.columns:
                c_str = str(c).strip()
                data[r_str][c_str] = cls._parse_val(df.loc[r, c])
        return cls(data=data, rows=rows, columns=columns)

    @classmethod
    def _read_csv_fp(
        cls,
        fp: Any,
        delimiter: str,
        index_col: int | str,
        strip_whitespace: bool,
    ) -> MetricsStore:
        reader = csv.reader(fp, delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration:
            return cls()

        if strip_whitespace:
            header = [h.strip() for h in header]

        # Determine index_col index
        if isinstance(index_col, str):
            if index_col in header:
                idx_pos = header.index(index_col)
            else:
                idx_pos = 0
        else:
            idx_pos = int(index_col)

        col_names = [h for i, h in enumerate(header) if i != idx_pos]

        data: dict[str, dict[str, Any]] = {}
        row_names: list[str] = []

        for line_num, row_cells in enumerate(reader, start=2):
            if not row_cells or all(not str(c).strip() for c in row_cells):
                continue
            if strip_whitespace:
                row_cells = [c.strip() for c in row_cells]

            if idx_pos < len(row_cells):
                row_name = row_cells[idx_pos]
            else:
                row_name = f"row_{len(row_names)}"

            if not row_name:
                row_name = f"row_{len(row_names)}"

            row_names.append(row_name)
            data[row_name] = {}

            col_idx = 0
            for i, cell in enumerate(row_cells):
                if i == idx_pos:
                    continue
                if col_idx < len(col_names):
                    c_name = col_names[col_idx]
                    data[row_name][c_name] = cls._parse_val(cell)
                    col_idx += 1

        return cls(data=data, rows=row_names, columns=col_names)

    @property
    def rows(self) -> list[str]:
        """List of row names."""
        return list(self._rows)

    @property
    def columns(self) -> list[str]:
        """List of column names."""
        return list(self._columns)

    @property
    def data(self) -> dict[str, dict[str, Any]]:
        """Raw dictionary of metrics."""
        return self._data

    def has_row(self, row: str) -> bool:
        """Check if row exists (case-sensitive)."""
        return row in self._data

    def has_column(self, col: str) -> bool:
        """Check if column exists."""
        return col in self._columns

    def has_metric(self, row: str, col: str) -> bool:
        """Check if both row and column exist."""
        return row in self._data and col in self._data[row]

    def get(self, row: str, col: str, default: Any = ...) -> Any:
        """Retrieve metric value for row and column.

        Raises MetricNotFoundError if row or column is not found and no default is provided.
        """
        row_clean = str(row).strip()
        col_clean = str(col).strip()

        if row_clean in self._data:
            row_dict = self._data[row_clean]
            if col_clean in row_dict:
                return row_dict[col_clean]

        # Case-insensitive fallback if exact match not found
        for r_k, r_v in self._data.items():
            if r_k.lower() == row_clean.lower():
                for c_k, c_v in r_v.items():
                    if c_k.lower() == col_clean.lower():
                        return c_v

        if default is not ...:
            return default

        # Generate helpful error message with close matches
        row_suggestions = difflib.get_close_matches(
            row_clean, self._rows, n=3, cutoff=0.5
        )
        col_suggestions = difflib.get_close_matches(
            col_clean, self._columns, n=3, cutoff=0.5
        )

        msg = f"Metric '{row_clean}.{col_clean}' not found in metrics store.\n"
        if row_clean not in self._data:
            msg += f"  Row '{row_clean}' not found. Available rows: {self._rows}"
            if row_suggestions:
                msg += f" (Did you mean: {row_suggestions}?)"
            msg += "\n"
        else:
            avail_cols = list(self._data[row_clean].keys())
            msg += f"  Column '{col_clean}' not found in row '{row_clean}'. Available columns: {avail_cols}"
            if col_suggestions:
                msg += f" (Did you mean: {col_suggestions}?)"
            msg += "\n"

        raise MetricNotFoundError(msg, row=row_clean, col=col_clean)

    def __getitem__(self, key: tuple[str, str] | str) -> Any:
        if isinstance(key, tuple) and len(key) == 2:
            return self.get(key[0], key[1])
        elif isinstance(key, str):
            if key in self._data:
                return self._data[key]
            raise KeyError(f"Row '{key}' not found. Available rows: {self._rows}")
        raise TypeError(f"Invalid key type: {type(key)}")

    def __contains__(self, key: tuple[str, str] | str) -> bool:
        if isinstance(key, tuple) and len(key) == 2:
            return self.has_metric(key[0], key[1])
        elif isinstance(key, str):
            return self.has_row(key)
        return False

    def __repr__(self) -> str:
        return f"MetricsStore(rows={len(self._rows)}, columns={len(self._columns)})"


def load_metrics(
    source: str | Path | Mapping[str, Mapping[str, Any]] | MetricsStore | Any,
    delimiter: str = ",",
    index_col: int | str = 0,
    **kwargs,
) -> MetricsStore:
    """Helper function to load metrics from any supported source."""
    if isinstance(source, MetricsStore):
        return source
    if isinstance(source, (str, Path)):
        return MetricsStore.from_csv(
            source, delimiter=delimiter, index_col=index_col, **kwargs
        )
    if isinstance(source, Mapping):
        return MetricsStore(data=source)
    if hasattr(source, "to_dict"):
        return MetricsStore.from_dataframe(source)
    raise TypeError(f"Cannot load metrics from source of type: {type(source)}")
