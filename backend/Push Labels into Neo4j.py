from neo4j import GraphDatabase
import pandas as pd

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j","password"))

def add_sla_label(tx, ticket_id, sla_label):
    tx.run(
        "MATCH (t:Ticket {id:$id}) "
        "SET t.sla_label = $sla_label",
        id=ticket_id, sla_label=int(sla_label)
    )

df = pd.read_csv("data/tickets/bilstm_features.csv")
df['sla_label'] = df['SLA For Resolution'].apply(
    lambda x: 1 if str(x).strip().lower() == 'met' else 0
)

with driver.session() as session:
    for _, row in df.iterrows():
        session.write_transaction(add_sla_label, row['Ticket ID'], row['sla_label'])

print("✅ SLA labels populated into Neo4j")
