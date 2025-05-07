import sympy as sp

from sympy import Symbol

from LIReC.lib.db_access import db
from LIReC.lib.pslq_utils import PreciseConstant

from pcf_identification_utils import verify_relation, evaluate_expression

def find_connections(pcf_object, anchor_objects, low_prec_req, low_eval_depth, high_prec_req, high_eval_depth, connection_thresh):

    def as_precise_constant(obj, prec, depth):
        res = evaluate_expression(obj, prec, depth)
        return (None, None) if res is None else (PreciseConstant(str(res[0]), res[2]), res[1])

    candidates = []
    verified_connections = []

    pcf_precise_constant, pcf_symbol = as_precise_constant(pcf_object, low_prec_req,low_eval_depth)
    if pcf_precise_constant is None:
        return []

    for anchor_object in anchor_objects:

        anchor_precise_constant, anchor_symbol = as_precise_constant(anchor_object, low_prec_req, low_eval_depth)

        if anchor_precise_constant is None:
            continue

        relation = db.identify([anchor_precise_constant, pcf_precise_constant], degree=2)
        
        if relation is not None and relation != []:
            candidates.append([relation[0], anchor_object])
    
    if candidates != []:

        pcf_precise_constant, pcf_symbol = as_precise_constant(pcf_object, high_prec_req, high_eval_depth)
        if pcf_precise_constant is None:
            return []
        
        for relation ,anchor in candidates:
            if "c1" in str(relation):

                anchor_precise_constant, anchor_symbol = as_precise_constant(pcf_object, high_prec_req, high_eval_depth)
                anchor_value = anchor_precise_constant.value

                if anchor_precise_constant is None:
                    continue

            else:
                anchor_value = None

            result, expr = verify_relation(relation, [pcf_precise_constant.value, anchor_value])
            if result is None:
                continue
            if result < connection_thresh:
                c0_symbol = Symbol('c0')
                eq = sp.Eq(expr, 0)
                c0_sol = sp.solve(eq, c0_symbol, dict=False)

                if c0_sol is not None and anchor is not None and anchor_symbol is not None:
                    verified_connections.append([c0_sol, anchor, anchor_symbol])
    
    return verified_connections


def all_related(objects, low_prec_req, low_eval_depth, high_prec_req, high_eval_depth, connection_thresh):
    """
    Returns True if all objects in `objects` are transitively related
    to each other (i.e., there's a path between every pair under the relation),
    otherwise returns False.

    Uses `find_connections`.
    """

    # Edge cases: 0 or 1 object => trivially related.
    if len(objects) <= 1:
        return True

    visited = set()
    queue = []

    # Start BFS from the first object
    visited.add(objects[0])
    queue.append(objects[0])

    while queue:
        current_pcf = queue.pop(0)
        
        # Find all potential connections from this object to unvisited objects
        anchors_to_check = [obj for obj in objects if obj not in visited]
        connections = find_connections(current_pcf, anchors_to_check, 
                                       low_prec_req=low_prec_req, low_eval_depth=low_eval_depth, 
                                       high_prec_req=high_prec_req, high_eval_depth=high_eval_depth, 
                                       connection_thresh=connection_thresh)
        # connections is of the form [ [c0_sol, anchor, anchor_symbol], ... ]

        if not connections:
            # If None or empty, no new valid connections from current
            continue

        found_any = len(connections) > 0
        
        # If we found any valid connections, we can add the anchors to the queue.
        if found_any:
            # We still have the (sol, anchor, anchor_symbol) info in `connections`;
            for (sol, anchor, anchor_symbol) in connections:
                if anchor not in visited:
                    visited.add(anchor)
                    queue.append(anchor)

    # If after BFS we've visited every object, they are all transitively related.
    return len(visited) == len(objects)