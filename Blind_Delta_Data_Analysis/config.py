# ─── config.py ───────────────────────────────────────────────
from dataclasses import dataclass
from typing import Tuple, List

@dataclass
class Config:
    file_name: str = "MetaData/DeltaSearch[3, 3]_-5_5.csv"
    cols: Tuple[str, ...] = (
        "FR_Delta", "c", "d", "convergence_c", "convergence_d"
    )
    anchor_file: str = "MetaData/blinddelta_related.txt"

    know_constans_file: str = "MetaData/constants.pkl"

    planes:  Tuple[Tuple[str, str]] = (
        ("FR_Delta", "d"),
        ("FR_Delta", "c"),
        ("FR_Delta", "convergence_d"),
        ("FR_Delta", "convergence_c")
    )

    grid_cell: float = 0.001
    dist_thresh: float = 0.01
    min_cluster: int = 5

    sample_limit: int = 400
    anchor_sample_limit: int = 4

    low_eval_depth: int = 1_000
    high_eval_depth: int = 2_000
    low_prec_req: int = 50
    high_prec_req: int = 150
    connection_thresh: float = 1e-50
