# utils.py (or near the top of the same file)
from collections import deque
from typing import Iterable, Callable, Tuple
import pandas as pd
from LIReC.lib.pcf import Poly, n
from datetime import datetime

def iter_spaces(
    original_df: pd.DataFrame,                 # <‑‑ keep the full table here
    metric_pairs: Iterable[tuple[str, str]],
    clustering_mgr,
):
    """
    Breadth‑first iterator over metric pairs.
    The queue carries *row subsets only*; we lazily re‑attach the required
    metric columns from `original_df` each time we pop.
    """
    housekeeping = ["pcf_key", "pcf_key_str", "related_objects"]
    queue: deque[tuple[pd.DataFrame, int]] = deque([(original_df[housekeeping].copy(), 0)])

    while queue:
        df, idx = queue.popleft()
        if idx >= len(metric_pairs):
            continue

        x, y = metric_pairs[idx]

        # --- re‑hydrate missing metric columns on demand -------------
        missing = [c for c in (x, y) if c not in df.columns]
        if missing:
            # pull only the needed rows & columns from the full dataset
            rows = original_df["pcf_key_str"].isin(df["pcf_key_str"])
            df = df.join(
                original_df.loc[rows, missing].set_index(original_df.loc[rows, "pcf_key_str"]),
                on="pcf_key_str",
            )

        spec_df = df[[x, y, *housekeeping]].copy()
        clustered = clustering_mgr.cluster_space(spec_df, x, y)

        if clustered is None:
            queue.append((df, idx + 1))
            continue

        # tiny closure to enqueue new *row* subsets
        def enqueue(new_df: pd.DataFrame, next_idx: int | None = None):
            queue.append((new_df[housekeeping].copy(), (idx + 1) if next_idx is None else next_idx))

        yield clustered, idx, (x, y), enqueue


def trace_tag(trace: list[int], planes: Tuple[Tuple[str, str]]) -> str:
    """
    Convert [4, 2, 1] → '(Metric_01, Metric02)C4_(Metric_11, Metric12)C2_(Metric_21, Metric22)C1'
    """
    return "_".join(f"({planes[i][0]},{planes[i][1]})C{cid}" for i, cid in enumerate(trace))

def cluster_fname(trace: list[int],
                  planes: Tuple[Tuple[str, str]],
                  suffix: str,
                  ext: str = ".png") -> str:
    tag  = trace_tag(trace, planes)
    ts   = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return f"{tag}__{suffix}__{ts}{ext}"


import subprocess, shutil
def current_git_sha(short=True):
    if not shutil.which("git"):
        return "nogit"
    try:
        cmd = ["git", "rev-parse", "--short" if short else "", "HEAD"]
        return subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError:
        return "norepo"



def pcf_to_key(pcf):

    a_coeffs = Poly(pcf.a.expr.subs({n: n}), n).all_coeffs()
    b_coeffs = Poly(pcf.b.subs({n: n}), n).all_coeffs()

    # Pad to length 3 if needed
    a_coeffs = ([0] * (3 - len(a_coeffs))) + a_coeffs if len(a_coeffs) < 3 else a_coeffs
    b_coeffs = ([0] * (3 - len(b_coeffs))) + b_coeffs if len(b_coeffs) < 3 else b_coeffs
    res = a_coeffs + b_coeffs

    return res