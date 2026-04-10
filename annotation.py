# ═══════════════════════════════════════════════════════════════════════════════
#  Operator descriptions & reasons
# ═══════════════════════════════════════════════════════════════════════════════

OPERATOR_DESCRIPTIONS = {
    # ── Scan operators ───────────────────────────────────────────────────────
    "Seq Scan":
        "The table is read using a sequential scan, examining every row from start to finish.",
    "Index Scan":
        "An index is used to locate matching rows, then the corresponding table rows are fetched.",
    "Index Only Scan":
        "The query is answered entirely from the index without accessing the table heap.",
    "Bitmap Heap Scan":
        "A bitmap of matching row locations is built from the index, then rows are fetched in bulk.",
    "Bitmap Index Scan":
        "An index is scanned to produce a bitmap of candidate row locations.",
    "Tid Scan":
        "Rows are fetched directly by their physical tuple identifier (ctid).",
    "Subquery Scan":
        "A subquery result is scanned as though it were a table.",
    "CTE Scan":
        "A Common Table Expression (WITH clause) result is scanned.",

    # ── Join operators ───────────────────────────────────────────────────────
    "Hash Join":
        "This join is implemented using a hash join operator — one input is hashed and the other is probed against it.",
    "Nested Loop":
        "Rows are combined using a nested loop: for each outer row, the inner input is scanned.",
    "Merge Join":
        "Two pre-sorted inputs are joined by advancing through them in order.",

    # ── Aggregate / Group operators ──────────────────────────────────────────
    "Hash Aggregate":
        "Grouping is performed by hashing the group-by keys.",
    "Group Aggregate":
        "Grouping is done over pre-sorted input by detecting group boundaries.",
    "Aggregate":
        "An aggregation operation (e.g., SUM, COUNT, AVG) is computed.",
    "GroupAggregate":
        "Grouping is done over pre-sorted input by detecting group boundaries.",

    # ── Sort / Order operators ───────────────────────────────────────────────
    "Sort":
        "Rows are sorted according to the specified key(s).",
    "Incremental Sort":
        "Rows are sorted incrementally, leveraging a partially pre-sorted input.",

    # ── Misc operators ───────────────────────────────────────────────────────
    "Limit":
        "Only the first N rows of the input are returned.",
    "Unique":
        "Duplicate rows are removed from the sorted input.",
    "Append":
        "Results from multiple sub-plans are concatenated.",
    "Materialize":
        "The input is materialized (stored in memory/disk) so it can be re-scanned.",
    "Gather":
        "Results from parallel workers are collected into a single stream.",
    "Gather Merge":
        "Sorted results from parallel workers are merge-collected.",
    "SetOp":
        "A set operation (UNION, INTERSECT, EXCEPT) is performed.",
    "WindowAgg":
        "A window function (e.g., ROW_NUMBER, RANK) is evaluated over partitions.",
    "Result":
        "A constant result is returned without scanning any table.",
}

OPERATOR_CHOICE_REASONS = {
    "Seq Scan":
        "This is likely because no suitable index exists on the filter columns, or the table is small enough that a full scan is cheaper than index lookup overhead.",
    "Index Scan":
        "An index on the relevant column(s) makes it cheaper to look up specific rows rather than scanning the entire table.",
    "Index Only Scan":
        "All required columns are available in the index itself, eliminating the need to access the table heap.",
    "Bitmap Heap Scan":
        "This approach is chosen when many rows match the filter — a bitmap avoids repeated random I/O while still leveraging the index.",
    "Hash Join":
        "Hashing one input allows O(1) lookups during the probe phase, making it efficient for large unsorted inputs.",
    "Nested Loop":
        "Nested loop is favored when one side of the join is very small or when an index is available on the inner relation.",
    "Merge Join":
        "Both inputs are already sorted (or cheaply sortable) on the join key, making a merge efficient.",
    "Hash Aggregate":
        "Hashing the group keys avoids having to sort the input first.",
    "Sort":
        "An explicit sort is needed to satisfy ORDER BY or to prepare input for a merge join / group aggregate.",
    "Materialize":
        "The inner relation is materialized to avoid re-executing it for every outer row in a nested loop.",
}

# Maps SQL clause keywords to the plan-node categories they relate to
SQL_CLAUSE_MAP = {
    "scan":      ["FROM", "TABLE"],
    "join":      ["JOIN", "WHERE"],
    "sort":      ["ORDER BY"],
    "aggregate": ["GROUP BY", "HAVING", "SUM", "COUNT", "AVG", "MIN", "MAX"],
    "limit":     ["LIMIT", "FETCH"],
}

# Classify node types into categories for color coding & clause matching
NODE_CATEGORIES = {
    "Seq Scan": "scan", "Index Scan": "scan", "Index Only Scan": "scan",
    "Bitmap Heap Scan": "scan", "Bitmap Index Scan": "scan", "Tid Scan": "scan",
    "Subquery Scan": "scan", "CTE Scan": "scan",
    "Hash Join": "join", "Nested Loop": "join", "Merge Join": "join",
    "Sort": "sort", "Incremental Sort": "sort",
    "Hash Aggregate": "aggregate", "Group Aggregate": "aggregate",
    "Aggregate": "aggregate", "GroupAggregate": "aggregate", "WindowAgg": "aggregate",
    "Limit": "limit",
}

# Color palette for each category (used by the GUI)
CATEGORY_COLORS = {
    "scan":      {"bg": "#065f46", "fg": "#a7f3d0", "border": "#34d399"},  # green
    "join":      {"bg": "#1e3a5f", "fg": "#93c5fd", "border": "#60a5fa"},  # blue
    "sort":      {"bg": "#78350f", "fg": "#fde68a", "border": "#fbbf24"},  # amber
    "aggregate": {"bg": "#4c1d95", "fg": "#c4b5fd", "border": "#a78bfa"},  # purple
    "limit":     {"bg": "#831843", "fg": "#fbcfe8", "border": "#f472b6"},  # pink
    "other":     {"bg": "#374151", "fg": "#d1d5db", "border": "#9ca3af"},  # gray
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Cost comparison helpers
# ═══════════════════════════════════════════════════════════════════════════════

def extract_plan_cost(plan):
    """Return the total cost of a plan node, or None if unavailable."""
    if not isinstance(plan, dict):
        return None
    return plan.get("Total Cost")


def compare_aqp_costs(qep, aqps):
    """
    Compare the QEP cost against each AQP.
    Returns a dict keyed by disabled operator name:
    {
        disabled_op: {
            "qep_cost":    float,
            "aqp_cost":    float,
            "delta":       float,
            "multiplier":  float,          # e.g., 7.2 means 7.2× more expensive
            "replacement_ops": set(...),
            "text":        str,            # human-readable comparison
        }
    }
    """
    qep_cost = extract_plan_cost(qep)
    comparisons = {}

    for disabled_operator, aqp_info in aqps.items():
        aqp_cost = aqp_info.get("cost") if isinstance(aqp_info, dict) else extract_plan_cost(aqp_info)
        replacement_ops = aqp_info.get("replacement_ops", set()) if isinstance(aqp_info, dict) else set()

        if qep_cost is None or aqp_cost is None:
            continue

        delta = aqp_cost - qep_cost
        if delta <= 0:
            continue

        multiplier = aqp_cost / qep_cost if qep_cost > 0 else float("inf")

        # Build human-readable explanation
        if replacement_ops:
            alt_names = ", ".join(sorted(replacement_ops))
            text = (
                f"Disabling {disabled_operator} increases the estimated cost "
                f"by {multiplier:.1f}× (from {qep_cost:.2f} to {aqp_cost:.2f}). "
                f"The planner would instead use: {alt_names}."
            )
        else:
            text = (
                f"Disabling {disabled_operator} increases the estimated cost "
                f"by {multiplier:.1f}× (from {qep_cost:.2f} to {aqp_cost:.2f})."
            )

        comparisons[disabled_operator] = {
            "qep_cost": qep_cost,
            "aqp_cost": aqp_cost,
            "delta": delta,
            "multiplier": multiplier,
            "replacement_ops": replacement_ops,
            "text": text,
        }

    return comparisons


# ═══════════════════════════════════════════════════════════════════════════════
#  SQL-to-plan line mapping
# ═══════════════════════════════════════════════════════════════════════════════

def find_target_line(sql_lines, node):
    """
    Determine which line of the SQL query a plan node most likely corresponds to.

    Strategy:
      1. If the node has a Relation Name, find the line containing that relation.
      2. Otherwise, use the node category to find a matching SQL clause keyword.
      3. Fall back to line 0.
    """
    node_type = node.get("Node Type", "")
    relation = node.get("Relation Name", "")
    alias = node.get("Alias", "")
    category = NODE_CATEGORIES.get(node_type, "other")

    # 1 — Match by relation name or alias
    if relation:
        for i, line in enumerate(sql_lines):
            low = line.lower()
            if relation.lower() in low:
                return i
        # Also try the alias
        if alias and alias != relation:
            for i, line in enumerate(sql_lines):
                if alias.lower() in line.lower():
                    return i

    # 2 — Match by SQL clause keywords for the node category
    keywords = SQL_CLAUSE_MAP.get(category, [])
    for kw in keywords:
        for i, line in enumerate(sql_lines):
            if kw.lower() in line.lower():
                return i

    # 3 — Special cases
    if "Join" in node_type or "Loop" in node_type:
        for i, line in enumerate(sql_lines):
            low = line.lower()
            if "join" in low or "where" in low:
                return i

    return 0


# ═══════════════════════════════════════════════════════════════════════════════
#  Annotation generation
# ═══════════════════════════════════════════════════════════════════════════════

def generate_annotations(qep, aqp_comparisons, sql_query):
    """
    Walk the QEP tree and produce an annotation list.
    Each annotation dict contains:
        node_type, relation, target_line_idx, text, category
    """
    sql_lines = sql_query.split("\n")
    annotations = []

    def traverse(node):
        node_type = node.get("Node Type", "")
        relation = node.get("Relation Name", "")
        category = NODE_CATEGORIES.get(node_type, "other")

        desc = OPERATOR_DESCRIPTIONS.get(node_type, "")
        if not desc:
            # Skip nodes we don't have descriptions for
            for child in node.get("Plans", []):
                traverse(child)
            return

        reason = OPERATOR_CHOICE_REASONS.get(node_type, "")

        # Get the AQP comparison data (may be dict with 'text' key or plain string)
        comp_data = aqp_comparisons.get(node_type, "")
        if isinstance(comp_data, dict):
            comparison = comp_data.get("text", "")
        else:
            comparison = comp_data

        parts = [p for p in [desc, reason, comparison] if p]
        full_text = "\n".join(parts)

        target_idx = find_target_line(sql_lines, node)

        annotations.append({
            "node_type": node_type,
            "relation": relation,
            "target_line_idx": target_idx,
            "text": full_text,
            "category": category,
        })

        for child in node.get("Plans", []):
            traverse(child)

    traverse(qep)

    # De-duplicate by (node_type, target_line_idx)
    unique_annotations = []
    seen = set()
    for anno in annotations:
        identifier = (anno["node_type"], anno["target_line_idx"])
        if identifier not in seen:
            seen.add(identifier)
            unique_annotations.append(anno)
    return unique_annotations


# ═══════════════════════════════════════════════════════════════════════════════
#  Annotated SQL generation (inline comments)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_annotated_sql(sql_query, annotations):
    """
    Produce a version of the SQL query with inline /* ... */ annotations
    inserted after the relevant lines.

    Example output:
        SELECT * FROM customer C,  /* Seq Scan: read sequentially ... */
        orders O
        WHERE C.c_custkey = O.o_custkey  /* Hash Join: ... */
    """
    lines = sql_query.split("\n")

    # Group annotations by target line
    line_annotations = {}
    for anno in annotations:
        idx = anno.get("target_line_idx", 0)
        line_annotations.setdefault(idx, []).append(anno)

    result_lines = []
    for i, line in enumerate(lines):
        if i in line_annotations:
            comments = []
            for anno in line_annotations[i]:
                # Compact single-line summary for inline comment
                short = _make_short_annotation(anno)
                comments.append(short)
            comment_str = "  /* " + " | ".join(comments) + " */"
            result_lines.append(line + comment_str)
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def _make_short_annotation(anno):
    """Build a compact annotation string suitable for an inline SQL comment."""
    node_type = anno.get("node_type", "")
    relation = anno.get("relation", "")
    text = anno.get("text", "")

    # Extract just the first sentence of the description
    first_sentence = text.split("\n")[0].rstrip(".")
    label = f"{node_type}"
    if relation:
        label += f" on {relation}"

    return f"{label}: {first_sentence}"