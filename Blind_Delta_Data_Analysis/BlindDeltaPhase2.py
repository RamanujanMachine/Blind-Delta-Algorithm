import ast

import matplotlib.pyplot as plt
import sympy as sp
import mpmath as mp

import random
from sympy import Symbol

from datetime import datetime
from pathlib import Path
import sys


from LIReC.lib.pcf import PCF
from LIReC.lib.db_access import db
from LIReC.lib.pslq_utils import PreciseConstant

from DF_Manager import DFManager
from ui_generic import BaseUI, ConsoleUI
from UnionFind import union_find_closure, build_dict_of_sets_with_strs
from ClusteringManager import ClusteringManager
from config import Config
from utils import iter_spaces, cluster_fname, trace_tag, current_git_sha
from pcf_connection import find_connections, all_related

from datetime import datetime
from pathlib import Path
import subprocess, json, csv
import glob
import yaml

CFG = Config()

flatten = lambda seq: [item for sub in seq for item in sub]

# Set global precision for mpmath
mp.mp.dps = 400

PRECISION_BUFFER = 1.3

run_ts  = datetime.now().strftime("%Y‑%m‑%dT%H‑%M‑%S")
git_sha = current_git_sha(short=True)
RUN_DIR = Path("results") / f"{run_ts}_run-{git_sha}"
RUN_DIR.mkdir(parents=True, exist_ok=True)

import logging

log_path = RUN_DIR / "run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),            # console
        logging.FileHandler(log_path, mode="w", encoding="utf-8"),  # file
    ],
    force=True,   # overwrite any prior basicConfig call
)

log = logging.getLogger(__name__)

# dump config + start log file
(RUN_DIR / "config.yaml").write_text(yaml.safe_dump(CFG.__dict__))
log_file = (RUN_DIR / "run.log").open("w")

def get_anchors(df):

    filtered_objects = df[["pcf_key_str", "related_objects"]]
    filtered_objects = filtered_objects[filtered_objects["related_objects"].apply(lambda x: len(x) > 0)]

    dict_of_sets = build_dict_of_sets_with_strs(filtered_objects)

    components = union_find_closure(dict_of_sets)

    group_info = {}

    for leader_str, pcfs_in_this_component in components.items():
        # Union of all constants used by PCFs in this component
        constants_in_this_component = set()
        anchor_pcfs = []

        for pcf_key_str in pcfs_in_this_component:
            anchor_key = ast.literal_eval(pcf_key_str)
            anchor_pcfs.append(PCF(anchor_key[:3],anchor_key[3:]))

            # dict_of_sets[pcf_str] is the set of constants related to this PCF
            constants_in_this_component.update(dict_of_sets[pcf_key_str])

        # Store result in group_info
        group_info[leader_str] = [anchor_pcfs, constants_in_this_component]

    number_of_leaders = len(components.keys())

    return group_info, number_of_leaders

def get_cluster_data(cluster_df):
    """
    Returns (anchor_pcfs, related_constants, pcfs) for a given cluster.
    """
    anchors_info, number_of_leaders = get_anchors(cluster_df)

    anchor_pcfs = []
    related_constants = []   
    if number_of_leaders != 0:

        info = list(anchors_info.values())

        anchor_pcfs = [group[0] for group in info] # [[anchor_pcfs], [anchor_pcfs], ...]
        related_constants = [group[1] for group in info] # [[related_constants], [related_constants], ...]
    
    unlabeled = cluster_df[~cluster_df["related_objects"].astype(bool)]
    pcfs = [[PCF(pcf_key[:3], pcf_key[3:]), str(pcf_key)] for pcf_key in unlabeled["pcf_key"]]
    
    return anchor_pcfs, related_constants, pcfs


def main():
    
    """
    # --- Stage 1: Data Import and Initial Clustering ---
    """

    df_manager = DFManager(
    data_file_name=CFG.file_name,
    columns_to_extract=list(CFG.cols),
    lirec_anchor_file=CFG.anchor_file,
    constants_file=CFG.know_constans_file,
    ui=ConsoleUI(),
    )
    df = df_manager.df

    clustering_manager = ClusteringManager(
    CFG.grid_cell,
    CFG.dist_thresh,
    CFG.min_cluster,
    )

    known_constants = df_manager._load_constants()
    
    for clustered_df, metric_idx, (x, y), enqueue in iter_spaces(df, CFG.planes, clustering_manager):
        
        log.info("Metric pair %s vs %s", x, y)
        fig, ax = clustering_manager.plot_clusters(clustered_df, x, y)

        plane_dir = RUN_DIR / f"{x}_vs_{y}"
        plane_dir.mkdir(parents=True, exist_ok=True)

        group_dir = plane_dir / f"{datetime.now():%Y_%m_%d_%H_%M_%S}"
        group_dir.mkdir(parents=True, exist_ok=True)

        fig.savefig(group_dir / f"scatter.png", dpi=300, bbox_inches="tight")
        
        # Group the results by Cluster_ID (ignoring noise with Cluster_ID == -1)
        for cluster_id, group in clustered_df.groupby('Cluster_ID'):

            cluster_dir = group_dir / f"cluster_{cluster_id}"
            cluster_dir.mkdir(parents=True, exist_ok=True)

            log.info("Cluster %s size: %d", cluster_id, len(group))
            if cluster_id == -1:
                continue

            df.loc[group.index, "trace"] = df.loc[group.index, "trace"].apply(
                lambda t, cid=cluster_id: [*t, cid]
            )

            resulting_connections = []
            new_connection_pcfs = 0

            anchor_pcfs, related_constants, pcfs = get_cluster_data(group)
            
            related_constants = flatten(related_constants)
            
            if related_constants == []:

                log.info("Cluster %s: No constants", cluster_id)


                sample_pcfs = random.sample(pcfs, min(CFG.anchor_sample_limit, len(pcfs)))

                for pcf, key in sample_pcfs:

                    connections = find_connections(pcf_object=pcf, anchor_objects=known_constants.values(), 
                                                   low_prec_req=CFG.low_prec_req, low_eval_depth=CFG.low_eval_depth, 
                                                   high_prec_req=CFG.high_prec_req, high_eval_depth=CFG.high_eval_depth, 
                                                   connection_thresh=CFG.connection_thresh)
                    
                    if connections: new_connection_pcfs += 1 

                    for sol, anchor_object, anchor_symbol in connections:
                        success = df_manager._add_related_object(df, key, anchor_symbol)
                        resulting_connections.append([key, sol, anchor_symbol])

                if len(resulting_connections) == 0:
                    log.info("Cluster %s: No constant-connections found", cluster_id)
            
            anchor_pcfs, related_constants, pcfs = get_cluster_data(group)
            related_constants = flatten(related_constants)

            if related_constants == [] and len(pcfs) >= CFG.anchor_sample_limit:
                sample_pcfs = random.sample(pcfs, min(CFG.sample_limit+CFG.anchor_sample_limit, len(pcfs)))
                potenial_anchors, samples = sample_pcfs[:CFG.anchor_sample_limit+1], sample_pcfs[CFG.anchor_sample_limit+1:]
                potenial_anchors = [x[0] for x in potenial_anchors]

                for pcf, key in samples:

                    connections = find_connections(pcf_object=pcf, anchor_objects=potenial_anchors, 
                                                   low_prec_req=CFG.low_prec_req, low_eval_depth=CFG.low_eval_depth, 
                                                   high_prec_req=CFG.high_prec_req, high_eval_depth=CFG.high_eval_depth, 
                                                   connection_thresh=CFG.connection_thresh)
                    
                    if connections: new_connection_pcfs += 1 
                    
                    for sol, anchor_object, anchor_symbol in connections:
                        success = df_manager._add_related_object(df, key, anchor_symbol)
                        resulting_connections.append([key, sol, anchor_symbol])

                if len(resulting_connections) == 0:
                    log.info("Cluster %s: No inter-connections found", cluster_id)
                    continue

            anchor_pcfs, related_constants, pcfs = get_cluster_data(group)
            related_constants = flatten(related_constants)

            constant_objects = []

            for constant in related_constants:
                if str(constant) in known_constants.keys():
                    constant_objects.append(known_constants[str(constant)])
                else:
                    pcf_key = ast.literal_eval(constant)
                    constant_objects.append(PCF(pcf_key[:3], pcf_key[3:]))

            are_constants_related = all_related(constant_objects, 
                                                low_prec_req = CFG.low_prec_req, low_eval_depth = CFG.low_eval_depth,
                                                high_prec_req = CFG.high_prec_req, high_eval_depth = CFG.high_eval_depth, 
                                                connection_thresh = CFG.connection_thresh)
            anchor_pcfs = flatten(anchor_pcfs)
            if are_constants_related:
                log.info("Cluster %d : %s",cluster_id, ", ".join(map(str, related_constants)))

                anchor_pcfs = anchor_pcfs + constant_objects

                sample_pcfs = random.sample(pcfs, min(CFG.sample_limit, len(pcfs)))

                for pcf, key in sample_pcfs:
                    connections = find_connections(pcf_object=pcf, anchor_objects=anchor_pcfs, 
                                                   low_prec_req=CFG.low_prec_req, low_eval_depth=CFG.low_eval_depth, 
                                                   high_prec_req=CFG.high_prec_req, high_eval_depth=CFG.high_eval_depth, 
                                                   connection_thresh=CFG.connection_thresh)
                    
                    if connections: new_connection_pcfs += 1 


                    log.info("%s: %s", key, connections)

                    for sol, anchor_object, anchor_symbol in connections:
                        success = df_manager._add_related_object(df, key, anchor_symbol)
                        resulting_connections.append([key, sol, anchor_symbol])
            else:
                log.info("Cluster %s: Multiple constants", cluster_id)
                # Prepare a new processing space using the next metric pair (if available)
                # Match rows from the original DataFrame by comparing string representations of pcf_key.
                keys_set = set(group['pcf_key_str'])
                new_space_df = clustered_df[clustered_df['pcf_key_str'].isin(keys_set)]
                enqueue(new_space_df)

            trace = df.loc[group.index[0], "trace"]

            header = (
                f"Trace:             : {trace_tag(trace, CFG.planes)}\n"
                f"# Metric pair      : {x} vs {y}\n"
                f"# Cluster ID       : {cluster_id}\n"
                f"# PCFs in cluster  : {len(group)}\n"
                f"# New connections  : {len(resulting_connections)}, for {new_connection_pcfs} unique PCFs\n"
                f"# Related constants: {', '.join(map(str, related_constants)) or '—'}\n"
                f"# Anchors          : {', '.join(str(a) for a in anchor_pcfs) or '—'}\n"
                "# ------------------------------------------------------------\n"
                "# key  :  c0_solution  :  anchor_symbol\n"
            )

            new_row = {
                "metric_x": x,
                "metric_y": y,
                "trace": trace_tag(trace, CFG.planes),
                "cluster_id_in_space": cluster_id,
                "pcfs": len(group),
                "new_connections": len(resulting_connections),
                "new_connection_pcfs": new_connection_pcfs,
                "constants": "|".join(map(str, related_constants)),
            }


            summary_path = RUN_DIR / "summary.csv"
            write_header = not summary_path.exists()
            with summary_path.open("a", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=new_row.keys())
                if write_header:
                    writer.writeheader()
                writer.writerow(new_row)

            with (cluster_dir / "connections.txt").open("w") as f:
                f.write(header)
                for key, sol, anchor_symbol in resulting_connections:
                    f.write(f"{key} : {sol} : {anchor_symbol}\n")
        
        log.info("Iteration complete!")

if __name__ == '__main__':

    main()

    artefacts = [
        str(p.relative_to(RUN_DIR)) 
        for p in RUN_DIR.rglob("*") if p.is_file() and p.suffix in {".png", ".txt"}
    ]
    (RUN_DIR / "artefacts.json").write_text(json.dumps(artefacts, indent=2))

    log.info("Done!")