from backend.agent import resolve_ticket
from backend.rag import query_rag

def handle_ticket(ticket):
    priority = ticket["Priority"].lower()

    if priority in ["low", "medium"]:
        # Autonomous resolution
        resolution_plan = resolve_ticket(ticket)
        print(f"✅ Auto‑resolved Ticket {ticket['Ticket ID']}")
        print(resolution_plan)
        # Mark as closed
        ticket["Status"] = "Closed"
        return resolution_plan

    elif priority == "high":
        # Suggest resolution only
        suggestions = query_rag(f"{ticket['Topic']} | {ticket['Priority']} | {ticket['Product group']}")
        print(f"⚠️ High Priority Ticket {ticket['Ticket ID']} → Human review required")
        print("Suggested resolutions:", suggestions)
        return suggestions

    else:  # Critical
        print(f"🚨 Critical Ticket {ticket['Ticket ID']} → Escalate to L3 support")
        return None
