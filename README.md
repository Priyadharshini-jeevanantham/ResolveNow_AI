# ResolveNow AI

ResolveNow AI is an intelligent IT service management (ITSM) project designed to help support teams handle incoming incidents more efficiently. The system combines machine learning, retrieval-augmented generation (RAG), and workflow automation to classify tickets, suggest solutions, route issues to the right agent, and monitor SLA deadlines.

## Project Summary

This project aims to reduce manual effort in incident handling by providing:

- AI-based ticket classification and priority prediction
- Knowledge-based solution suggestions using a curated knowledge base
- Agent assignment and escalation support
- SLA monitoring and alerting
- A dashboard for viewing ticket activity and support workflow
- A report-generation pipeline for documentation and presentation

## What the System Does

ResolveNow AI processes new support tickets by analyzing their text, predicting priority and issue category, checking whether a similar known issue exists in the knowledge base, and then taking the appropriate next step. It can:

- assign the ticket to an appropriate support agent
- send email notifications for high-priority or escalated issues
- provide suggested resolutions from the knowledge base
- help track whether a ticket is approaching SLA limits

## Key Components

### 1. Backend API
The main backend service is implemented in [backend/api.py](backend/api.py). It exposes the core FastAPI endpoints for processing tickets, serving the dashboard, and coordinating AI workflows.

### 2. RAG and Knowledge Retrieval
The retrieval layer in [backend/rag.py](backend/rag.py) uses sentence embeddings and FAISS indexing to search relevant solutions from the knowledge base.

### 3. Dashboard
The web dashboard in [frontend/dashboard.html](frontend/dashboard.html) provides a user-friendly interface for monitoring ticket status and support operations.

### 4. Report Generation
The report generation script in [build_capstone_report.py](build_capstone_report.py) creates a professional Word report for the capstone project.

## Important Files

- [backend/api.py](backend/api.py) — main FastAPI application and ticket processing logic
- [backend/rag.py](backend/rag.py) — RAG-based retrieval and explainability flow
- [frontend/dashboard.html](frontend/dashboard.html) — dashboard UI
- [build_capstone_report.py](build_capstone_report.py) — report generation script
- [backend/agent_roster.py](backend/agent_roster.py) — agent assignment logic
- [backend/sla_service.py](backend/sla_service.py) — SLA monitoring and deadline calculations

## Tech Stack

- Python
- FastAPI
- Scikit-learn
- FAISS
- Sentence Transformers
- Pandas and NumPy
- HTML/CSS/JavaScript for the dashboard

## How to Run

1. Create and activate a Python environment.
2. Install the required dependencies.
3. Start the backend API:

```bash
uvicorn backend.api:app --reload --port 8000
```

4. Open the dashboard in the browser or access the API endpoints.

## Notes

This project is designed as an AI-assisted ITSM solution and can be extended with more advanced models, additional integrations, and richer analytics in the future.
