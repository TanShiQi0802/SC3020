"""Helpers for annotating and normalising PostgreSQL execution plans."""


def clean_result_nodes(node):
    """Remove ``Result`` nodes by promoting their children into ``Plans``.

    The function walks the plan tree recursively. For every child under
    ``node["Plans"]``:
    - if the child is a ``Result`` node, its cleaned children are promoted
      directly into the current node's ``Plans`` list
    - otherwise, the cleaned child is kept as-is

    Args:
        node (dict): A PostgreSQL plan node.

    Returns:
        dict: The same node, updated in place with redundant ``Result`` nodes
        removed from its subtree.
    """
    if not isinstance(node, dict):
        return node

    new_children = []
    for child in node.get("Plans", []):
        cleaned_child = clean_result_nodes(child)

        if cleaned_child.get("Node Type") == "Result":
            new_children.extend(cleaned_child.get("Plans", []))
        else:
            new_children.append(cleaned_child)

    if "Plans" in node:
        node["Plans"] = new_children

    return node


# Tree-normalisation helpers

MERGE_PAIRS = {
    "Hash Join": "Hash",
    "Bitmap Heap Scan": "Bitmap Index Scan",
    "Merge Join": "Sort",
    "Aggregate": "Sort",
    "Unique": "Sort",
}


def merge_plan_pairs(node):
    """Collapse redundant single-child wrapper nodes defined in ``MERGE_PAIRS``.

    For example, if a ``Hash Join`` has a single ``Hash`` child, the ``Hash``
    node is treated as structural noise and its children are promoted into the
    parent. The merged child node type is recorded in ``node["_merged"]``.

    Args:
        node (dict): A PostgreSQL plan node.

    Returns:
        dict: The same node, updated in place with redundant wrapper nodes
        removed from its subtree.
    """
    if not isinstance(node, dict):
        return node

    cleaned_children = [merge_plan_pairs(child) for child in node.get("Plans", [])]
    if "Plans" in node:
        node["Plans"] = cleaned_children

    expected_child_type = MERGE_PAIRS.get(node.get("Node Type"))
    if not expected_child_type or len(cleaned_children) != 1:
        return node

    only_child = cleaned_children[0]
    if only_child.get("Node Type") != expected_child_type:
        return node

    node["Plans"] = only_child.get("Plans", [])
    node["_merged"] = expected_child_type
    return node
