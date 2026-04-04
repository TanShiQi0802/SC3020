"""
1. tree cleaning (from NEURON paper): remove "result " nodes
- initialise new_child sublist
- go into ['Plans'], check node type for every sublist, if it's "Result" promote its children
- if not then add to new_child
- in the end set original node ["Plans"] to new_child
""" 


"""
2. Merge pairs as per neuron paper
MERGE_PAIRS = {
    "Hash Join":        "Hash",
    "Bitmap Heap Scan": "Bitmap Index Scan",
    "Merge Join":       "Sort",
    "Aggregate":        "Sort",
    "Unique":           "Sort",
}
- get node type and look up in MERGE_PAIRS
- check if the node has only one child matching the expected type (indicating redudant node)
- set this node's children to the duplicate node's children (replace ["Plans"])
- add attribute ["_merged"]= child type to dict to keep record
- return node
"""

"""
3. Hardcode annotations
- create dict of operations and their defs and when postgresql prefers it

OPERATOR_DESCRIPTIONS = {
    "Seq Scan":    "...",
    "Index Scan":  "...",
    "Hash Join":   "...",
    # etc
}

OPERATOR_CHOICE_REASONS = {
    "Seq Scan":    "...",
    "Hash Join":   "...",
    # etc
}

source MOCHA PAPER:

Seq Scan → preferred when table is small or most rows are read
Index Scan → preferred when filter is highly selective
Hash Join → preferred for large unsorted non-indexed inputs
Nested Loop → preferred when outer is small and inner is indexed
Merge Join → preferred when both inputs are already sorted
Hash Aggregate → preferred when distinct groups fit in memory
"""

"""
4. aqp comparison
- for every node being annotated in qep, for that node
- for current qep node compute relation set using get_relations from preprocessing.py (helper)
- search aqp for a node having the same relation set (if same op type skip)
- compare cost of qep and aqp
- hardcode justifications when cost gap is small/large

"""

"""
5. annotating node
- take one node and produce annotation
- look up node type in operator descriptions and return hardcoded explanation
- why part: look up node type and reason in the dict defined before
- vs (cost) : write cost justification vs qep
"""

"""
6. interface connector
- given a query generate qep
- clean tree (1st 2 fns here)
- traverse tree in postorder (children before parent)
    - for each node, annotate node(node, aqps), and return operator description, operator choice and comparison with aqps
"""

"""
note

use helper fns from preprocessing.py (get_relations, get qep, get_aqps,)
"""