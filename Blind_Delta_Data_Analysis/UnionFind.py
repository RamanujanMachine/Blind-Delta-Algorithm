class UnionFind:
    def __init__(self, elements):
        self.parent = {e: e for e in elements}
    
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, a, b):
        rootA, rootB = self.find(a), self.find(b)
        if rootA != rootB:
            self.parent[rootB] = rootA

def union_find_closure(dict_of_sets):
    """
    Creates a union-find on the keys of dict_of_sets.
    Merges them if they share any element in their sets.

    Returns a dict { representative_str: set_of_str_keys_in_that_component }
    """
    # Gather all string keys
    keys = list(dict_of_sets.keys())
    
    # Initialize union-find on these keys
    uf = UnionFind(keys)
    
    # Invert the dictionary: for each related string, which keys refer to it?
    from collections import defaultdict
    constant_to_keys = defaultdict(list)
    for k, rel_set in dict_of_sets.items():
        for c in rel_set:
            constant_to_keys[c].append(k)
    
    # Union all keys that share a constant
    for c, related_keys in constant_to_keys.items():
        for i in range(len(related_keys) - 1):
            uf.union(related_keys[i], related_keys[i+1])
    
    # Group keys by their final representative
    groups = {}
    for k in keys:
        leader = uf.find(k)
        groups.setdefault(leader, set()).add(k)
    
    return groups


def build_dict_of_sets_with_strs(group):
    """
    Given a DataFrame 'group' with columns: 
      'pcf_key_str' -> a single PCF key of type str
      'related_objects' -> a list of PCF keys (of type str) and constants,
    build:

    1) dict_of_sets: {pcf_key_str: set_of_pcf_key_strs}
    """

    dict_of_sets = {}

    # Iterate over rows, converting each PCF to string
    for idx, row in group.iterrows():
        pcf_key_str = row["pcf_key_str"]
        rel_objs = row["related_objects"]

        # Convert each related object to string
        related_strs = set(obj for obj in rel_objs)

        # Assign to dict_of_sets
        dict_of_sets[pcf_key_str] = related_strs

    return dict_of_sets
