from neo4j import GraphDatabase
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

def export_graph():
    """Export graph data from Neo4j into PyTorch Geometric format."""
    with driver.session() as session:
        # Get tickets
        nodes = session.run("MATCH (t:Ticket) RETURN t.id AS id, t.priority AS priority, t.topic AS topic, t.sla_label AS sla_label")
        edges = session.run("MATCH (t:Ticket)-[:RESOLVED_BY]->(r:Resolution) RETURN t.id AS src, r.text AS dst")

        node_map = {}
        x = []
        y = []
        for i, record in enumerate(nodes):
            node_map[record["id"]] = i
            # Encode priority numerically
            priority_map = {"Critical":4,"High":3,"Medium":2,"Low":1}
            x.append([priority_map.get(record["priority"],0)])
            # SLA label (1 = Met, 0 = Breach)
            y.append(record["sla_label"] if record["sla_label"] is not None else 0)

        edge_index = []
        for record in edges:
            src = node_map[record["src"]]
            dst = len(node_map) + hash(record["dst"]) % 1000  # simple encoding for resolution nodes
            edge_index.append([src, dst])

        x = torch.tensor(x, dtype=torch.float)
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        y = torch.tensor(y, dtype=torch.long)

        data = Data(x=x, edge_index=edge_index, y=y)
        return data


class GraphSAGENet(torch.nn.Module):
    """GraphSAGE model for SLA prediction."""
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return F.log_softmax(x, dim=1)


def train_model(data, epochs=50):
    """Train GraphSAGE model on SLA labels."""
    model = GraphSAGENet(in_channels=1, hidden_channels=16, out_channels=2)  # 2 classes: SLA Met / Breach
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    for epoch in range(epochs):
        optimizer.zero_grad()
        out = model(data.x, data.edge_index)
        loss = F.nll_loss(out, data.y)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss {loss.item():.4f}")

    return model


def predict_sla(model, data, ticket_idx):
    """Predict SLA outcome for a given ticket index."""
    out = model(data.x, data.edge_index)
    pred = out[ticket_idx].argmax().item()
    return "SLA Met" if pred == 1 else "SLA Breach Risk"


if __name__ == "__main__":
    # Example usage
    data = export_graph()
    model = train_model(data, epochs=50)

    # Predict SLA for first ticket
    result = predict_sla(model, data, ticket_idx=0)
    print("Prediction for Ticket 0:", result)
