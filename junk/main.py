import psycopg2
import json

conn = psycopg2.connect(host="localhost",dbname="test_db", user="postgres",password="tjain0303",port=5433)
conn.autocommit=True

cur=conn.cursor()

# Create Fake Tables

cur.execute("""
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS customers;
    
    CREATE TABLE customers (
        id SERIAL PRIMARY KEY,
        name TEXT,
        city TEXT
    );
    
    CREATE TABLE orders (
        id SERIAL PRIMARY KEY,
        customer_id INT,
        amount NUMERIC
    );
    
    INSERT INTO customers (name, city) VALUES
        ('Alice', 'Singapore'), ('Bob', 'New York'), ('Carol', 'London');
    
    INSERT INTO orders (customer_id, amount) VALUES
        (1, 500), (1, 200), (2, 800), (3, 150), (2, 300);
""")

def get_qep(conn,sql):
    """
    sql:string: query to be executed,
    conn:psycopg2 connection object: connection objetc in psycopg2
    
    output:
    query execution plan 
    """
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {sql};")
        result = cur.fetchone()[0] 
        return result[0]["Plan"] # root node
    
def walk_plan(node, depth=0):
    indent=" "*depth
    node_type=node.get("Node Type","Unknown")
    relation=node.get("Relation Name","")
    total_cost=node.get("Total Cost",0)
    
    label=f"{node_type}"
    
    if relation:
        label+=f" on {relation}"
    
    print(f"{indent}[{label}]={total_cost}")
    
    for child in node.get("Plans",[]):
        walk_plan(child,depth+1)
        
def get_relations(node):
    """Collect all base table names in a subtree."""
    relations = set()
    if "Relation Name" in node:
        relations.add(node["Relation Name"])
    for child in node.get("Plans", []):
        relations |= get_relations(child) # set union operation
    return relations


queries = {
    "single_table":     "SELECT * FROM customers WHERE city = 'Singapore'",
    "two_table_join":   "SELECT c.name, o.amount FROM customers c JOIN orders o ON c.id = o.customer_id",
    "with_aggregation": "SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name",
    "with_sort":        "SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name ORDER BY SUM(o.amount) DESC",
}

for label, q in queries.items():
    print(f"\n{'='*40}")
    print(f"Query: {label}")
    print('='*40)
    plan = get_qep(conn, q)
    walk_plan(plan)
        
         
      
"""
For future debugging purposes this is what the node dictionary looks like.
NOTE: Getting root node will return something like this:
{                           +
"Plan": {                 +
"Node Type": "Seq Scan",+
"Relation Name": "foo", +
"Alias": "foo",         +
"Startup Cost": 0.00,   +
"Total Cost": 155.00,   +
"Plan Rows": 10000,     +
"Plan Width": 4         +
}                         +
}

This is one node in the Query Tree.

NOTE: Relation Names only really appear in leaf node outputs. The intermediate steps usually don't have relation names. 
helper get_relations() does exactly this. We use it to collect all Relation Names from a node's subtree.
"""
    
