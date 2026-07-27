def predict_sla(model, data, ticket_idx):
    out = model(data.x, data.edge_index)
    pred = out[ticket_idx].argmax().item()
    return "SLA Met" if pred==1 else "SLA Breach Risk"
