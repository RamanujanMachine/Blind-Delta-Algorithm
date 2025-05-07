# ────────────────────────────────────────────────────────────────
# df_manager.py
# ────────────────────────────────────────────────────────────────

from __future__ import annotations

import ast
import glob
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import dill
import pandas as pd

from ui_generic import BaseUI

from LIReC.lib.pcf import PCF, Poly, n


class Mathematical_Constant:
    """Simple container for a named constant."""

    def __init__(self, name: str, value, precision):
        self.name = name
        self.value = value
        self.precision = precision

    # –– helpers ––
    def eval(self, **_kwargs):
        return self

    def __str__(self):
        return f"{self.name} : {self.precision}"


# ────────────────────────────────────────────────────────────────
# Data‑frame manager
# ────────────────────────────────────────────────────────────────


class DFManager:
    """Light‑weight wrapper around a pandas DataFrame + helper I/O."""

    # ------------------------------------------------------------------
    def __init__(
        self,
        *,
        data_file_name: str | None = None,
        columns_to_extract: List[str] | None = None,
        lirec_anchor_file: str = "",
        constants_file: str = "",
        load_from_pickle_if_exists: bool = True,
        ui: BaseUI | None = None,
    ):
        self.data_file_name = data_file_name
        self.columns_to_extract = columns_to_extract
        self.lirec_anchor_file = lirec_anchor_file
        self.constants_file = constants_file
        self._load_from_pickle_if_exists = load_from_pickle_if_exists
        self.ui = ui or BaseUI()

        # will be populated lazily
        self.df = pd.DataFrame()
        if data_file_name:
            self.df = self.load_data()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    def load_data(self):
        # 1) resolve glob patterns → list[Path]
        file_list = self._expand_paths(self.data_file_name)

        df_list = []
        for file_path in self.ui.file_iterator(file_list, desc="Loading files"):
            df_temp = self._read_single_file(Path(file_path))
            df_list.append(df_temp)

        df_merged = pd.concat(df_list, ignore_index=True)
        self.add_constants_and_anchors(df_merged)
        return df_merged

    # ------------------------------------------------------------------
    # INTERNALS – file helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _expand_paths(pattern: str | Path) -> List[str]:
        pattern = str(pattern)
        if any(ch in pattern for ch in "*?"):
            matches = glob.glob(pattern)
            if not matches:
                raise ValueError(f"No files match pattern: {pattern}")
            return matches
        return [pattern]

    def _read_single_file(self, file_path: Path) -> pd.DataFrame:
        base = str(file_path.with_suffix(""))
        pkl_path = base + ".pkl"
        if self._load_from_pickle_if_exists and Path(pkl_path).exists():
            with open(pkl_path, "rb") as fh:
                return dill.load(fh)
        df_temp = self._import_csv(file_path)
        with open(pkl_path, "wb") as fh:
            dill.dump(df_temp, fh)
        return df_temp

    # ------------------------------------------------------------------
    # CSV → DataFrame
    # ------------------------------------------------------------------
    def _import_csv(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_csv(file_path)

        # keep only requested numeric columns + first (pcf_key) column
        first_col = df.columns[0]
        use_cols = (
            df.columns if self.columns_to_extract is None else [first_col] + self.columns_to_extract
        )
        df = df[use_cols]

        # pcf_key → list[int]
        df[first_col] = df[first_col].apply(lambda x: [int(i) for i in ast.literal_eval(str(x).strip())])

        # coerce numeric + drop NaNs
        for c in df.columns:
            if c != first_col:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df.dropna(subset=[c for c in df.columns if c != first_col], inplace=True)

        # housekeeping columns
        df.rename(columns={first_col: "pcf_key"}, inplace=True)
        df["pcf_key_str"] = df["pcf_key"].apply(str)
        df["pcf_obj"] = None
        df["cluster_ID"] = -1
        df["trace"] = [[] for _ in range(len(df))]
        df["related_objects"] = [[] for _ in range(len(df))]

        # remove sentinel rows
        numeric_cols = [c for c in df.columns if c not in ("pcf_key", "pcf_obj", "related_objects")]
        df = df[(df[numeric_cols] != -1010).all(axis=1)]
        return df

    # ------------------------------------------------------------------
    # Constants & anchors – domain specific
    # ------------------------------------------------------------------
    def add_constants_and_anchors(self, df: pd.DataFrame):
        known_constants = (
            self._load_constants() if self.constants_file and os.path.exists(self.constants_file) else {}
        )
        if not (self.lirec_anchor_file and os.path.exists(self.lirec_anchor_file)):
            return

        anchors = self._import_anchors_from_LIREC()
        total = len(anchors)

        # progress bar ---------------------------------------------------
        self.ui.start_progress_bar(total, title="Loading constants")

        added: List[Tuple[str, str]] = []
        failed: List[Tuple[str, str]] = []
        unknown: List[Tuple[str, str]] = []

        for i, (coeffs, const_name) in enumerate(anchors):
            if const_name in known_constants:
                const_obj = known_constants[const_name]
                success = self._add_related_object(df, str(coeffs), const_obj.name)
                (added if success else failed).append((coeffs, const_name))
                status = "added" if success else "failed"
            else:
                unknown.append((coeffs, const_name))
                status = "unknown"
            self.ui.update_progress_bar(i, status)

        summary = {"added": added, "failed": failed, "unknown": unknown}
        self.ui.finish_progress_bar(summary)

        # write a Markdown table with details
        self._write_anchor_table("Constant_Loading.md", added, failed, unknown)

    # ------------------------------------------------------------------
    # helpers – constants / anchors
    # ------------------------------------------------------------------
    def _load_constants(self):
        constants: Dict[str, Mathematical_Constant] = {}
        with open(self.constants_file, "rb") as fh:
            for name, value, precision in pickle.load(fh):
                constants[name] = Mathematical_Constant(name, value, precision)
        return constants

    def _import_anchors_from_LIREC(self):
        identified = []
        with open(self.lirec_anchor_file, "r", encoding="utf-8") as fh:
            for line in fh:
                if len(line) <= 9:
                    continue
                try:
                    _key, val = line.split(" [[")
                    val_parts = val.split(";")
                    if len(val_parts) <= 1:
                        continue
                    canonical = eval("[[" + val_parts[0])
                    pcf_obj = PCF.from_canonical_form(canonical)
                    constant = val_parts[1].rstrip().rstrip("]")
                    identified.append((pcf_obj, constant))
                except Exception:
                    continue

        # shift small‑degree PCFs into ±5 window so coefficients are bounded
        in_bounds = []
        for pcf_obj, constant in identified:
            a_orig, b_orig = pcf_obj.a.expr, pcf_obj.b.expr
            for shift in range(-5, 6):
                a_coeffs = Poly(a_orig.subs({n: n + shift}), n).all_coeffs()
                b_coeffs = Poly(b_orig.subs({n: n + shift}), n).all_coeffs()
                a_coeffs = ([0] * (3 - len(a_coeffs))) + a_coeffs if len(a_coeffs) < 3 else a_coeffs
                b_coeffs = ([0] * (3 - len(b_coeffs))) + b_coeffs if len(b_coeffs) < 3 else b_coeffs
                coeffs = a_coeffs + b_coeffs
                if any(abs(k) > 5 for k in coeffs):
                    continue
                in_bounds.append((coeffs, constant))
                if pcf_obj.a.degree() == 0 and pcf_obj.b.degree() == 0:
                    break
        return in_bounds

    def _add_related_object(self, df: pd.DataFrame, pcf_key_str: str, obj_symbol: str) -> bool:
        idx = df.index[df["pcf_key_str"] == pcf_key_str]
        if not idx.empty:
            df.at[idx[0], "related_objects"].append(obj_symbol)
            return True
        return False

    # ------------------------------------------------------------------
    # misc public helpers
    # ------------------------------------------------------------------
    def add_column(self, column_name: str, default_value=None):
        if column_name in self.df.columns:
            print(f"Column '{column_name}' already exists. Skipping.")
            return
        self.df[column_name] = default_value

    def append_row(self, row_dict):
        self.df = pd.concat([self.df, pd.DataFrame([row_dict])], ignore_index=True)

    def save_to_pickle(self, pkl_path: str | Path):
        with open(pkl_path, "wb") as fh:
            dill.dump(self.df, fh)
        print(f"DataFrame saved to {pkl_path}.")

    def load_from_pickle(self, pkl_path: str | Path):
        if not os.path.exists(pkl_path):
            raise ValueError(f"File {pkl_path} does not exist")
        with open(pkl_path, "rb") as fh:
            self.df = dill.load(fh)
        print(f"DataFrame loaded from {pkl_path}.")

    # ------------------------------------------------------------------
    # markdown helper
    # ------------------------------------------------------------------
    @staticmethod
    def _write_anchor_table(
        path: str,
        added: List[Tuple[str, str]],
        failed: List[Tuple[str, str]],
        unknown: List[Tuple[str, str]],
    ):
        """Dump a 3‑way, width‑padded Markdown table summarising anchor status."""

        rows = max(len(added), len(failed), len(unknown))
        pad = lambda lst: lst + [("", "")] * (rows - len(lst))  # noqa: E731
        added, failed, unknown = map(pad, (added, failed, unknown))

        cols = [
            [str(x[0]) for x in added],
            [str(x[1]) for x in added],
            [str(x[0]) for x in failed],
            [str(x[1]) for x in failed],
            [str(x[0]) for x in unknown],
            [str(x[1]) for x in unknown],
        ]
        sub_headers = ["key", "const"] * 3
        widths = [max(len(h), *(len(cell) for cell in col)) for h, col in zip(sub_headers, cols)]
        group_w = [widths[0] + widths[1] + 3, widths[2] + widths[3] + 3, widths[4] + widths[5] + 3]

        def fmt(row, align="<"):
            return "| " + " | ".join(f"{cell:{align}{w}}" for cell, w in zip(row, widths)) + " |"

        lines = []
        group_titles = ["Added", "Failed", "Unknown"]
        group_cells = [f"{title:^{w}}" for title, w in zip(group_titles, group_w)]
        lines.append("| " + " | ".join(group_cells) + " |")
        lines.append(fmt(sub_headers, align="^"))
        lines.append("|-" + "-|-".join("-" * w for w in widths) + "-|")

        for cells in zip(*cols):
            lines.append(fmt(cells))

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
