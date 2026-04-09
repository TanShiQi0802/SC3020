import psycopg2

GUC_MAP = {
    "Seq Scan": "enable_seqscan",
    "Index Scan": "enable_indexscan",
    "Index Only Scan": "enable_indexonlyscan",
    "Bitmap Heap Scan": "enable_bitmapscan",
    "Nested Loop": "enable_nestloop",
    "Hash Join": "enable_hashjoin",
    "Merge Join": "enable_mergejoin",
    "Hash Aggregate": "enable_hashagg",
    "Sort": "enable_sort",
}

MERGE_PAIRS = {
    "Hash Join": "Hash",
    "Bitmap Heap Scan": "Bitmap Index Scan",
    "Merge Join": "Sort",
    "Aggregate": "Sort",
    "Unique": "Sort",
}

def get_connection(host, dbname, user, password, port):
    if psycopg2 is None:
        raise ImportError("psycopg2 is required to connect to PostgreSQL.")
    conn = psycopg2.connect(host=host, dbname=dbname, user=user, password=password, port=port)
    conn.autocommit = True
    return conn

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

def get_all_aqps(conn, sql, root):
    node_types = get_node_types(root)
    aqps = {}
    for node_type in node_types:
        guc = GUC_MAP.get(node_type, None)
        if guc is None: continue
        aqp = get_aqp(conn, sql, [guc])
        aqps[node_type] = aqp
    return aqps