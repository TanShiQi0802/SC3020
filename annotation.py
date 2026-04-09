OPERATOR_DESCRIPTIONS = {
    "Seq Scan": "Tables are read using sequential scan from start to finish.",
    "Index Scan": "Uses an index to find matching rows first, then fetches the corresponding table rows.",
    "Hash Join": "This join is implemented using the hash join operator.",
    "Nested Loop": "Combines rows by scanning the inner input repeatedly.",
    "Merge Join": "Joins two sorted inputs by advancing through them in order."
}

OPERATOR_CHOICE_REASONS = {
    "Seq Scan": "This is likely because no index is created on the tables, or reading the whole table is cheaper.",
    "Hash Join": "NL joins and merge join likely increase the estimated cost significantly.",
}

def extract_plan_cost(plan):
    if not isinstance(plan, dict):
        return None
    return plan.get("Total Cost")

def compare_aqp_costs(qep, aqps):
    qep_cost = extract_plan_cost(qep)
    comparisons = {}

    for disabled_operator, aqp in aqps.items():
        aqp_cost = extract_plan_cost(aqp)
        if qep_cost is None or aqp_cost is None:
            continue
            
        delta = aqp_cost - qep_cost
        if delta > 0:
            comparisons[disabled_operator] = f"Disabling {disabled_operator} increases estimated cost to {aqp_cost:.2f}."
            
    return comparisons

def find_target_line(sql_lines, node):
    node_type = node.get("Node Type", "")
    relation = node.get("Relation Name", "")

    if relation:
        for i, line in enumerate(sql_lines):
            if relation.lower() in line.lower():
                return i
    
    if "Join" in node_type or "Loop" in node_type:
        for i, line in enumerate(sql_lines):
            if "where" in line.lower() or "join" in line.lower():
                return i
    return 0
        
def generate_annotations(qep, aqp_comparisons, sql_query):
    sql_lines = sql_query.split("\n")
    annotations = []
    
    def traverse(node):
        node_type = node.get("Node Type", "")
        relation = node.get("Relation Name", "")
        
        if node_type in OPERATOR_DESCRIPTIONS:
            desc = OPERATOR_DESCRIPTIONS[node_type]
            reason = OPERATOR_CHOICE_REASONS.get(node_type, "")
            comparison = aqp_comparisons.get(node_type, "")
            
            full_text = f"{desc}\n{reason}\n{comparison}".strip()

            target_idx = find_target_line(sql_lines, node)
            
            annotations.append({
                "node_type": node_type,
                "relation": relation,
                "target_line_idx": target_idx,
                "text": full_text
            })
            
        for child in node.get("Plans", []):
            traverse(child)
            
    traverse(qep)

    unique_annotations = []
    seen = set()
    for anno in annotations:
        identifier = (anno["node_type"], anno["target_line_idx"])
        if identifier not in seen:
            seen.add(identifier)
            unique_annotations.append(anno)
    return unique_annotations
        