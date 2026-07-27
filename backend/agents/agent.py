from openai import OpenAI
from backend.rag import query_rag

client = OpenAI()

def resolve_ticket(ticket):
    query = f"{ticket['Topic']} | {ticket['Priority']} | {ticket['Product group']}"
    candidates = query_rag(query, k=1)
    resolution = candidates[0]['resolution']

    prompt = f"""
    Incident details:
    Topic: {ticket['Topic']}
    Priority: {ticket['Priority']}
    Product: {ticket['Product group']}
    SLA: {ticket['SLA For Resolution']}

    Suggested resolution from KEDB: {resolution}

    Please generate a structured incident resolution plan.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role":"user","content":prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    ticket = {
        "Topic":"Network Issue",
        "Priority":"Critical",
        "Product group":"Cloud",
        "SLA For Resolution":"Met"
    }
    print(resolve_ticket(ticket))
