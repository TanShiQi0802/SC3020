import psycopg2

# Utilise GUC config params (https://techdocs.broadcom.com/us/en/vmware-tanzu/data-solutions/tanzu-greenplum/7/greenplum-database/ref_guide-config_params-guc-list.html)
# Toggle off in sequence to generate alternative query plans

GUC_MAP = {
    "Seq Scan":         "enable_seqscan",
    "Index Scan":       "enable_indexscan",
    "Index Only Scan":  "enable_indexonlyscan",
    "Bitmap Heap Scan": "enable_bitmapscan",
    "Nested Loop":      "enable_nestloop",
    "Hash Join":        "enable_hashjoin",
    "Merge Join":       "enable_mergejoin",
    "Hash Aggregate":   "enable_hashagg",
    "Sort":             "enable_sort",
}

#TODO: ADD enable_material ,enable_partitionwise_join,

def get_connection(host,dbname,user,password,port):
    conn=psycopg2.connect(host=host,dbname=dbname,user=user,password=password,port=port)
    conn.autocommit=True
    return conn

def get_qep(conn,sql):
    cur=conn.cursor()
    cur.execute(f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {sql}")
    result=cur.fetchone()[0]
    return result[0]["Plan"]

def get_aqp(conn,sql,disabled_gucs):
    """Get alternative query plans by toggling guc values on and off (forcing the program to generate alternate trees when it cant use a certain type of node) 
        At this point we use a toggle-off one at a time system but going forward we can explore implementing every possible combination of the guc operators present in the tree.
    Args:
        conn (psycopg2 Connection): db connection
        sql (string): sql command to be executed
        disabled_gucs (_type_): _description_

    Returns:
        _type_: _description_
    """

    with conn.cursor() as cur:
        for guc in disabled_gucs:
            cur.execute(f"SET {guc} = off")
        
        plan=get_qep(conn,sql)
        
        for guc in disabled_gucs:
            cur.execute(f"SET {guc} = on")
    
    return plan


def get_node_types(node):
    """This tells get_all_aqps() which operators to disable when
    generating alternative plans.

    Args:
        node (Dictionary): node of the tree derived from get_qep
    """
    types={node.get("Node Type")}
    for child in node.get("Plans",[]):
        types|=get_node_types(child)
    return types
        
def get_all_qeps(conn,sql,root):
    """get all query execution plans for a given sql command.

    Args:
        conn (Connection object): psycopg2 connection for db
        sql (string): sql query to be executed
        root (dict): root node of the tree

    Returns:
        aqps(dict): dictionary of all possible query plans by disabling every operator in turn
    """
    node_types=get_node_types(root)
    aqps={}
    for type in node_types:
        guc=GUC_MAP.get(type,None)
        if guc==None: continue
        
        aqp=get_aqp(conn,sql,[guc])
        aqps[type]=aqp
    return aqps


def get_relations(node):
    """Collect all base table names in a subtree."""
    relations = set()
    if "Relation Name" in node:
        relations.add(node["Relation Name"])
    for child in node.get("Plans", []):
        relations |= get_relations(child) # set union operation
    return relations