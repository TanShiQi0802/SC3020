import psycopg2

GUC_MAP = {
    "Seq Scan":         "enable_seqscan",
    "Index Scan":       "enable_indexscan",
    "Index Only Scan":  "enable_indexonlyscan",
    "Bitmap Heap Scan": "enable_bitmapscan",
    "Bitmap Index Scan":"enable_bitmapscan",
    "Tid Scan":         "enable_tidscan",
    "Nested Loop":      "enable_nestloop",
    "Hash Join":        "enable_hashjoin",
    "Merge Join":       "enable_mergejoin",
    "Hash Aggregate":   "enable_hashagg",
    "Sort":             "enable_sort",
    "Materialize":      "enable_material",
    "Gather Merge":     "enable_gathermerge",
}

MERGE_PAIRS = {
    "Hash Join":        "Hash",
    "Bitmap Heap Scan": "Bitmap Index Scan",
    "Merge Join":       "Sort",
    "Aggregate":        "Sort",
    "Unique":           "Sort",
}

def get_connection(host, dbname, user, password, port):
    conn = psycopg2.connect(
        host=host, dbname=dbname, user=user, password=password, port=port
    )
    conn.autocommit = True
    return conn


def get_databases(host, user, password, port):
    try:
        conn = psycopg2.connect(
            host=host, dbname="postgres", user=user, password=password, port=port
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT datname FROM pg_database "
                "WHERE datistemplate = false ORDER BY datname"
            )
            databases = [row[0] for row in cur.fetchall()]
        conn.close()
        return databases
    except Exception:
        return []

def clean_result_nodes(node):
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


def merge_plan_pairs(node):
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


def normalize_plan(plan):
    cleaned_plan = clean_result_nodes(plan)
    return merge_plan_pairs(cleaned_plan)

def get_qep(conn, sql):
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {sql}")
        result = cur.fetchone()[0]
    plan = result[0]["Plan"]
    return normalize_plan(plan)


def get_aqp(conn, sql, disabled_gucs):
    with conn.cursor() as cur:
        for guc in disabled_gucs:
            cur.execute(f"SET {guc} = off")
        plan = get_qep(conn, sql)
        for guc in disabled_gucs:
            cur.execute(f"SET {guc} = on")
    return plan

def get_node_types(node):
    nodetype = node.get("Node Type")
    types = {nodetype} if nodetype else set()
    for child in node.get("Plans", []):
        types |= get_node_types(child)
    return types


def get_node_types_list(node):
    result = []
    nodetype = node.get("Node Type")
    if nodetype:
        result.append(nodetype)
    for child in node.get("Plans", []):
        result.extend(get_node_types_list(child))
    return result


def find_replacement_operators(qep, aqp, disabled_type):
    qep_types = get_node_types(qep)
    aqp_types = get_node_types(aqp)

    new_in_aqp = aqp_types - qep_types

    qep_list = get_node_types_list(qep)
    aqp_list = get_node_types_list(aqp)

    replacements = set(new_in_aqp)
    for op in aqp_types:
        if op != disabled_type and aqp_list.count(op) > qep_list.count(op):
            replacements.add(op)

    replacements.discard(disabled_type)
    replacements.discard("Result")

    return replacements


def get_all_aqps(conn, sql, root):
    node_types = get_node_types(root)
    qep_cost = root.get("Total Cost", 0)
    aqps = {}

    for node_type in node_types:
        guc = GUC_MAP.get(node_type)
        if guc is None:
            continue
        aqp = get_aqp(conn, sql, [guc])
        aqp_cost = aqp.get("Total Cost", 0)

        replacement_ops = find_replacement_operators(root, aqp, node_type)

        aqps[node_type] = {
            "plan": aqp,
            "cost": aqp_cost,
            "qep_cost": qep_cost,
            "replacement_ops": replacement_ops,
        }

    return aqps