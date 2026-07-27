from sentence_transformers import SentenceTransformer
import faiss, json
import shap
import evaluate
import numpy as np

# ── Load RAG components ───────────────────────────────
model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("models/faiss_index/kedb.index")
kedb = json.load(open("data/kedb/kedb.json"))

# ── Query RAG ─────────────────────────────────────────
def query_rag(query, k=3):
    embedding = model.encode([query])
    D, I = index.search(embedding, k)
    results = [kedb[idx] for idx in I[0]]
    return results

# ── SHAP Explainability ───────────────────────────────
explainer = shap.Explainer(model.encode, masker=shap.maskers.Text())

def explain_query(query):
    shap_values = explainer([query])
    shap.plots.text(shap_values[0])   # interactive visualization in notebook/IDE

# ── Evaluation Metrics (ROUGE + F1) ───────────────────
rouge = evaluate.load("rouge")
f1_metric = evaluate.load("f1")

def evaluate_rag(query, retrieved, reference):
    # retrieved: list of strings (solutions from KEDB)
    # reference: ground truth solution string
    rouge_scores = rouge.compute(
        predictions=[" ".join(retrieved)],
        references=[reference]
    )
    f1_scores = f1_metric.compute(
        predictions=[" ".join(retrieved)],
        references=[reference]
    )
    return {"rouge": rouge_scores, "f1": f1_scores}

# ── Run Evaluation Loop ───────────────────────────────
if __name__ == "__main__":
    test_queries = [
        {
            "query": "Critical Network Issue in Cloud",
            "reference": "Check network connectivity, verify DNS settings, restart network adapter."
        },
        {
            "query": "Hardware Failure in laptop",
            "reference": "Run hardware diagnostics, check device manager for errors, verify physical connections."
        },
        {
            "query": "Software Bug in application",
            "reference": "Clear application cache, reinstall affected software, apply latest patches."
        }
    ]

    for test in test_queries:
        q = test["query"]
        ref = test["reference"]

        print("\n🔎 Query:", q)
        answers = query_rag(q)
        retrieved_solutions = [ans.get("solution_suggestion", "") for ans in answers]

        # Print retrieved solutions
        for i, ans in enumerate(retrieved_solutions, 1):
            print(f"Result {i}: {ans}")

        # Explain with SHAP
        print("📊 SHAP Explanation (see visualization window)...")
        explain_query(q)

        # Evaluate with ROUGE + F1
        scores = evaluate_rag(q, retrieved_solutions, ref)
        print("✅ Evaluation Scores:", scores)
