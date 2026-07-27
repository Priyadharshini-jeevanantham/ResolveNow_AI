from neo4j import GraphDatabase

# Connect to Neo4j (make sure Neo4j is running locally)
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def add_ticket(tx, ticket_id, topic, priority, resolution):
    tx.run(
        "MERGE (t:Ticket {id:$id, topic:$topic, priority:$priority}) "
        "MERGE (r:Resolution {text:$resolution}) "
        "MERGE (t)-[:RESOLVED_BY]->(r)",
        id=ticket_id, topic=topic, priority=priority, resolution=resolution
    )

def build_graph():
    import json
    kedb = json.load(open("data/kedb/kedb.json"))
    with driver.session() as session:
        for entry in kedb:
            session.write_transaction(
                add_ticket, entry['id'], entry['topic'], entry['priority'], entry['resolution']
            )
    print("✅ Knowledge graph built in Neo4j")

if __name__ == "__main__":
    build_graph()
