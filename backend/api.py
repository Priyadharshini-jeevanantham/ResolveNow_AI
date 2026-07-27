# backend/api.py
# Run: uvicorn backend.api:app --reload --port 8000

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from backend.database.database import SessionLocal
from backend.database.database import engine
from backend.database.models import Ticket
from backend.database.models import Base
from backend.database.models import Ticket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pickle
import json
import os
import re
import uuid
import urllib.error
import urllib.request
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.sparse import hstack, csr_matrix
import warnings
warnings.filterwarnings('ignore')
from pathlib import Path
from dotenv import load_dotenv
from backend.agent_roster import assign_agent, get_all_current_agents, update_agent
from backend.email_service import (
    send_solution_email,
    send_high_priority_email,
    send_escalation_email, 
    send_sla_warning_email     # ← NEW: used when user says "Still Having Issue"
)
# ADD this line with the other imports:
from backend.sla_service import calculate_sla_deadlines, check_sla_status, get_sla_remaining, get_sla_warning_status

# Load .env from root folder explicitly
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="ResolveNow AI", version="1.0.0")

Base.metadata.create_all(bind=engine)

@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the ResolveNow AI dashboard."""
    dashboard_path = "frontend/dashboard.html"
    if not os.path.exists(dashboard_path):
        return HTMLResponse("<h2>Dashboard file not found. Place dashboard.html in frontend/dashboard.html</h2>")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ── CORS ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LOAD ALL MODELS ON STARTUP ─────────────────────────────────
print("Loading ResolveNow AI models...")

def load_model(path):
    with open(path, "rb") as f:
        return pickle.load(f)

try:
    priority_model = load_model("models/priority_model.pkl")
    topic_model    = load_model("models/topic_model.pkl")
    tfidf          = load_model("models/tfidf.pkl")
    priority_enc   = load_model("models/priority_enc.pkl")
    topic_enc      = load_model("models/topic_enc.pkl")
    agent_enc      = load_model("models/agent_enc.pkl")
    source_enc     = load_model("models/source_enc.pkl")
    product_enc    = load_model("models/product_enc.pkl")

    with open("data/kedb/kedb_from_data.json") as f:
        KEDB = json.load(f)

    print(f"All models loaded. KEDB has {len(KEDB)} known issues.")
    MODELS_READY = True
except Exception as e:
    print(f"Model loading failed: {e}")
    print("Run python backend/train_model.py first.")
    MODELS_READY = False


# ── REQUEST / RESPONSE MODELS ──────────────────────────────────
class NewTicket(BaseModel):
    topic: str
    source: str = "Email"
    product_group: str = "Cloud"
    support_level: str = "L2"
    agent_group: str = "General Support"
    description: str = ""
    country: str = "Unknown"
    created_by: str = "User"
    user_priority: str = ""
    user_email: str = ""

class TicketUpdate(BaseModel):
    ticket_id: str
    status: str
    resolution_notes: str = ""
    agent_name: str = ""


def extract_ticket_id_from_text(text: str) -> Optional[str]:
    """Extract ResolveNow ticket IDs from speech transcripts."""
    if not text:
        return None

    normalized = text.upper()
    ticket_match = re.search(r"\bTCKT[\s-]*(\d+)\b", normalized)
    if ticket_match:
        return f"TCKT-{ticket_match.group(1)}"

    number_match = re.search(r"\b(\d{5,})\b", normalized)
    if number_match:
        return f"TCKT-{number_match.group(1)}"

    return None


def transcribe_with_sarvam(audio_bytes: bytes, filename: str, content_type: str, language_code: str) -> str:
    api_key = (os.getenv("SARVAM_API_KEY") or os.getenv("SARVAM_SUBSCRIPTION_KEY") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Sarvam API key missing. Add SARVAM_API_KEY to your .env file."
        )

    endpoint = os.getenv("SARVAM_STT_URL")
    if not endpoint:
        endpoint = f"{os.getenv('SARVAM_API_ENDPOINT', 'https://api.sarvam.ai').rstrip('/')}/speech-to-text"
    model = os.getenv("SARVAM_STT_MODEL", "saarika:v2.5")
    lang = os.getenv("SARVAM_LANGUAGE_CODE", language_code or "unknown")
    boundary = f"----ResolveNow{uuid.uuid4().hex}"

    def field_part(name, value):
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    body = bytearray()
    body.extend(field_part("model", model))
    body.extend(field_part("language_code", lang))
    body.extend(
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename or "voice.webm"}"\r\n'
            f"Content-Type: {content_type or 'audio/webm'}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        endpoint,
        data=bytes(body),
        headers={
            "api-subscription-key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise HTTPException(status_code=e.code, detail=f"Sarvam STT failed: {detail}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sarvam STT request failed: {e}")

    transcript = (
        data.get("transcript")
        or data.get("text")
        or data.get("transcription")
        or ""
    )

    if not transcript and isinstance(data.get("transcripts"), list) and data["transcripts"]:
        first = data["transcripts"][0]
        if isinstance(first, dict):
            transcript = first.get("transcript") or first.get("text") or ""

    return transcript.strip()

# ── CORE AI LOGIC ──────────────────────────────────────────────
def encode_safe(encoder, value, default=0):
    try:
        return encoder.transform([value])[0]
    except:
        return default

def predict_priority_and_topic(topic, source, product_group, agent_group):
    """Use ML models to predict priority and issue type."""
    text = f"{topic} {source} {product_group}"
    text_vec = tfidf.transform([text])

    src_enc      = encode_safe(source_enc, source)
    prod_enc     = encode_safe(product_enc, product_group)
    agent_enc_val = encode_safe(agent_enc, agent_group)

    numeric = csr_matrix([[src_enc, prod_enc, agent_enc_val]])
    X = hstack([text_vec, numeric])

    priority_pred   = priority_model.predict(X)[0]
    priority_proba  = priority_model.predict_proba(X)[0]
    priority_label  = priority_enc.inverse_transform([priority_pred])[0]
    priority_confidence = float(max(priority_proba))

    topic_pred  = topic_model.predict(X)[0]
    topic_proba = topic_model.predict_proba(X)[0]
    topic_label = topic_enc.inverse_transform([topic_pred])[0]
    topic_confidence = float(max(topic_proba))

    return {
        "predicted_priority":   priority_label,
        "priority_confidence":  round(priority_confidence * 100, 1),
        "predicted_topic":      topic_label,
        "topic_confidence":     round(topic_confidence * 100, 1)
    }

def check_kedb(topic):
    """Check if issue exists in KEDB."""
    if topic in KEDB:
        return KEDB[topic]
    for key in KEDB:
        if key.lower() in topic.lower() or topic.lower() in key.lower():
            return KEDB[key]
    return None

def process_ticket(ticket_id, ticket_data):
    """
    Core AI decision engine.

    HIGH / CRITICAL  + known issue   → assign to agent + email agent WITH solution suggestion
    HIGH / CRITICAL  + unknown issue → assign to agent + email agent (no solution)
    LOW  / MEDIUM    + known issue   → email user with solution + Solved/Still Having Issue buttons
    LOW  / MEDIUM    + unknown issue → assign to agent, set In Progress
    """
    topic      = ticket_data["topic"]
    priority   = ticket_data["predicted_priority"]
    is_high    = priority.strip().lower() in ["high", "critical"]
    kedb_entry = check_kedb(topic)
    is_known   = kedb_entry is not None

    result = {
        "ticket_id":           ticket_id,
        "priority":            priority,
        "is_known_issue":      is_known,
        "action_taken":        "",
        "solution_suggestion": None,
        "resolution_steps":    None,
        "auto_resolved":       False,
        "auto_closed":         False,
        "assigned_to_group":   ticket_data.get("agent_group", "General Support"),
        "requires_human":      False,
        "kedb_match":          None,
        "email_required":      False,
        "message":             "",
        "timestamp":           datetime.now().isoformat()
    }

    # ── CASE 1: HIGH / CRITICAL PRIORITY ──────────────────────
    if is_high:
        result["requires_human"] = True

        if is_known:
            # Known high-priority — give solution suggestion to assignee
            result["action_taken"]        = "SUGGESTION_ONLY"
            result["solution_suggestion"] = kedb_entry["solution_suggestion"]
            result["resolution_steps"]    = kedb_entry["resolution_steps"]
            result["kedb_match"]          = kedb_entry["topic"]
            result["message"] = (
                f"HIGH PRIORITY ticket. Known issue detected: '{kedb_entry['topic']}'. "
                f"Solution suggestion sent to assignee. Human agent must evaluate and resolve."
            )
        else:
            # Unknown high-priority — pure human escalation
            result["action_taken"] = "ESCALATED_TO_HUMAN"
            result["message"] = (
                f"HIGH PRIORITY ticket. Unknown issue type. "
                f"Escalated to {result['assigned_to_group']} for human evaluation."
            )
        return result

    # ── CASE 2: LOW / MEDIUM PRIORITY ─────────────────────────
    if is_known:
        # Known issue — send solution to user, wait for confirmation
        result["action_taken"]        = "EMAIL_SENT_PENDING_CUSTOMER"
        result["solution_suggestion"] = kedb_entry["solution_suggestion"]
        result["resolution_steps"]    = kedb_entry["resolution_steps"]
        result["kedb_match"]          = kedb_entry["topic"]
        result["auto_resolved"]       = False
        result["auto_closed"]         = False
        result["requires_human"]      = False
        result["email_required"]      = True
        result["assigned_to_group"] = kedb_entry.get("typical_agent_group", result["assigned_to_group"])
        result["assigned_to"]       = "Pending Customer Confirmation"
        result["message"] = (
            f"LOW/MEDIUM PRIORITY. Known issue: '{kedb_entry['topic']}'. "
            f"Solution email sent to user. Awaiting customer confirmation."
        )
    else:
        # Unknown issue — assign to agent
        result["action_taken"]   = "PREDICTED_AND_ASSIGNED"
        result["auto_resolved"]  = False
        result["email_required"] = False
        result["message"] = (
            f"LOW/MEDIUM PRIORITY. New/unknown issue. "
            f"Assigned to {result['assigned_to_group']} for resolution."
        )

    return result


# ── API ENDPOINTS ──────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "system":        "ResolveNow AI",
        "status":        "running",
        "models_ready":  MODELS_READY,
        "kedb_size":     len(KEDB) if MODELS_READY else 0,
        "total_tickets": len(TICKETS)
    }

@app.get("/health")
def health():
    return {"status": "ok", "models_ready": MODELS_READY}


@app.post("/voice/ticket-status")
async def voice_ticket_status(
    audio: UploadFile = File(...),
    language_code: str = Form("unknown")
):
    """
    Transcribe a spoken incident number with Sarvam STT and return ticket status.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    transcript = transcribe_with_sarvam(
        audio_bytes=audio_bytes,
        filename=audio.filename or "voice.webm",
        content_type=audio.content_type or "audio/webm",
        language_code=language_code
    )
    ticket_id = extract_ticket_id_from_text(transcript)

    if not ticket_id:
        return {
            "success": False,
            "transcript": transcript,
            "message": "I could not detect a ticket number. Please say the incident number again."
        }

    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            return {
                "success": False,
                "transcript": transcript,
                "ticket_id": ticket_id,
                "message": f"I heard {ticket_id}, but no matching ticket was found."
            }

        assignee = ticket.assigned_to or ticket.assigned_group or "the support team"
        spoken_response = (
            f"Ticket {ticket.ticket_id} is currently {ticket.status}. "
            f"The priority is {ticket.priority}. "
            f"It is assigned to {assignee}."
        )

        return {
            "success": True,
            "transcript": transcript,
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "priority": ticket.priority,
            "topic": ticket.topic,
            "assigned_to": ticket.assigned_to,
            "assigned_group": ticket.assigned_group,
            "created_time": ticket.created_time,
            "spoken_response": spoken_response
        }
    finally:
        db.close()


@app.post("/tickets/create")
def create_ticket(ticket: NewTicket):

    db = SessionLocal()

    """
    Create a new ticket — AI analyses and decides action automatically.

    Decision tree:
      HIGH/CRITICAL + known issue   → assign agent + email agent with solution
      HIGH/CRITICAL + unknown issue → assign agent + email agent (no solution)
      LOW/MEDIUM    + known issue   → email user with solution + confirm buttons
      LOW/MEDIUM    + unknown issue → assign agent, set In Progress
    """
    global TICKET_COUNTER

    if not MODELS_READY:
        raise HTTPException(status_code=503, detail="Models not loaded. Run train_model.py first.")
    print("========== DEBUG ==========")
    # Get latest ticket from database
    last_ticket = (
        db.query(Ticket)
        .order_by(Ticket.id.desc())
        .first()
)
    print("LAST TICKET:", last_ticket.ticket_id if last_ticket else "NONE")
    
    if last_ticket:
        last_number = int(last_ticket.ticket_id.split("-")[1])
        next_number = last_number + 1
    else:
         next_number = 100050

    ticket_id = f"TCKT-{next_number}"

    print("NEW TICKET:", ticket_id)
    print("===========================")

    # ML prediction
    predictions = predict_priority_and_topic(
        ticket.topic, ticket.source, ticket.product_group, ticket.agent_group
    )

    # User priority overrides ML if provided
    final_priority = ticket.user_priority.strip() if ticket.user_priority.strip() else predictions["predicted_priority"]

    # Build ticket record
    ticket_record = {
        "ticket_id":              ticket_id,
        "topic":                  ticket.topic,
        "description":            ticket.description,
        "source":                 ticket.source,
        "product_group":          ticket.product_group,
        "support_level":          ticket.support_level,
        "agent_group":            ticket.agent_group,
        "country":                ticket.country,
        "created_by":             ticket.created_by,
        "user_email":             ticket.user_email,
        "created_time":           datetime.now().isoformat(),
        "status":                 "New",
        "predicted_priority":     final_priority,
        "ml_suggested_priority":  predictions["predicted_priority"],
        "priority_set_by":        "user" if ticket.user_priority.strip() else "ai",
        "predicted_topic":        predictions["predicted_topic"],
        "topic_confidence":       predictions["topic_confidence"],
        "priority_confidence":    predictions["priority_confidence"]
    }
    # Attach SLA deadlines at ticket creation time
    ticket_record["sla"] = calculate_sla_deadlines(
    created_time = ticket_record["created_time"],
    priority     = final_priority
)

    # Run AI decision engine
    ai_result = process_ticket(ticket_id, ticket_record)

    ticket_is_high = final_priority.strip().lower() in ["high", "critical"]

    # ── HIGH / CRITICAL: assign agent + email agent ─────────────
    if ticket_is_high:
        # Auto-assign agent
        try:
            auto_group, auto_agent_name, auto_agent_email = assign_agent(ticket.agent_group)
        except Exception:
            auto_group      = ticket.agent_group
            auto_agent_name = "Support Team"
            auto_agent_email = os.getenv("FALLBACK_AGENT_EMAIL", "")

        ticket_record["status"]           = "In Progress"
        ticket_record["assigned_to"]      = auto_agent_name
        ticket_record["assigned_group"]   = auto_group
        ticket_record["assigned_email"]   = auto_agent_email
        ai_result["assigned_agent"]       = auto_agent_name
        ai_result["assigned_agent_email"] = auto_agent_email
        ai_result["assigned_to"]    = auto_agent_name
        ai_result["assigned_group"] = auto_group

        # Email assignee — include solution if known issue
        if auto_agent_email:
            agent_email_result = send_high_priority_email(
                to_email    = auto_agent_email,
                ticket_id   = ticket_id,
                topic       = ticket.topic,
                priority    = final_priority,
                solution    = ai_result.get("solution_suggestion"),
                steps       = ai_result.get("resolution_steps", []),
                is_known    = ai_result.get("is_known_issue", False),
                agent_group = auto_group,
                agent_name  = auto_agent_name,
                created_by  = ticket.created_by,
                description = ticket.description,
                # In create_ticket(), in the high-priority email call, add:
                sla_info = ticket_record.get("sla")
            )
            ticket_record["agent_email_sent"]   = agent_email_result.get("success", False)
            ticket_record["agent_email_status"] = agent_email_result.get("message", "")
            ai_result["agent_email_sent"]        = agent_email_result.get("success", False)
            print(f"  {'✅' if agent_email_result.get('success') else '❌'} Agent email → {auto_agent_email}")
        else:
            ticket_record["agent_email_sent"]   = False
            ticket_record["agent_email_status"] = "No agent email configured"

        # Acknowledgement to user
        if ticket.user_email:
            send_high_priority_email(
       to_email    = ticket.user_email,
       ticket_id   = ticket_id,
       topic       = ticket.topic,
       priority    = final_priority,
       solution    = None,
       steps       = [],
       is_known    = False,
       agent_group = auto_group,
       agent_name  = ticket.created_by,   # ← use the USER's name for the greeting
       created_by  = ticket.created_by,
       description = (
           f"Your {final_priority} priority ticket has been assigned to "
           f"{auto_agent_name} from {auto_group}. They will contact you shortly."
       )
   )
            ticket_record["user_ack_sent"] = True
            print(f"  ✅ User acknowledgement sent to {ticket.user_email}")

    # ── LOW / MEDIUM + KNOWN ISSUE: email user with solution ────
    elif ai_result.get("email_required"):
        ticket_record["status"] = "Pending Customer"

        email_result = {"success": False, "message": "No email provided"}

        if ticket.user_email:
            email_result = send_solution_email(
                to_email   = ticket.user_email,
                ticket_id  = ticket_id,
                topic      = ticket.topic,
                solution   = ai_result.get("solution_suggestion", ""),
                steps      = ai_result.get("resolution_steps", []),
                created_by = ticket.created_by
            )

        ticket_record["email_sent"]   = email_result.get("success", False)
        ticket_record["email_status"] = email_result.get("message", "")
        ai_result["email_sent"]       = email_result.get("success", False)
        ai_result["email_status"]     = email_result.get("message", "")
        print(f"  {'✅' if email_result.get('success') else '❌'} Solution email → {ticket.user_email}")

    # ── LOW / MEDIUM + UNKNOWN ISSUE: assign, set In Progress ───
    elif ai_result.get("auto_closed"):
        ticket_record["status"]          = "Closed"
        ticket_record["resolution_time"] = datetime.now().isoformat()
    elif ai_result.get("auto_resolved"):
        ticket_record["status"]          = "Resolved"
        ticket_record["resolution_time"] = datetime.now().isoformat()
    else:
        ticket_record["status"] = "In Progress"

    ticket_record["ai_result"] = ai_result

    db_ticket = Ticket(
    ticket_id      = ticket_id,
    topic          = ticket.topic,
    description    = ticket.description,
    priority       = final_priority,
    status         = ticket_record["status"],
    created_by     = ticket.created_by,
    user_email     = ticket.user_email,
    assigned_to    = ticket_record.get("assigned_to"),
    assigned_group = ticket_record.get("assigned_group"),
    created_time   = ticket_record["created_time"],
    ai_result      = ai_result
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    return {
        "success":     True,
        "ticket_id":   ticket_id,
        "ticket":      ticket_record,
        "ai_analysis": ai_result
    }


@app.get("/tickets/{ticket_id}/confirm", response_class=HTMLResponse)
def confirm_ticket(ticket_id: str, action: str = "close", resolved: str = "yes"):
    """
    User clicks email link to confirm resolution.
    resolved=yes → close ticket in DB
    resolved=no  → escalate to agent, send escalation email
    """
    db = SessionLocal()
    try:
        # ── Load from DATABASE ─────────────────────────────────
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()

        if not ticket:
            return HTMLResponse(f"""
            <html><body style="font-family:Arial;background:#F8FAFC;
                                display:flex;align-items:center;justify-content:center;
                                height:100vh;margin:0;">
              <div style="text-align:center;padding:2rem;background:#fff;
                          border-radius:16px;border:1px solid #E2E8F0;">
                <div style="font-size:48px;margin-bottom:1rem;">❌</div>
                <h2 style="color:#EF4444;">Ticket Not Found</h2>
                <p style="color:#6B7280;">Ticket {ticket_id} does not exist.</p>
              </div>
            </body></html>
            """, status_code=404)

        # ── USER SAYS: ISSUE RESOLVED ──────────────────────────
        if resolved == "yes":
            ticket.status           = "Closed"
            ticket.close_time       = datetime.now().isoformat()
            ticket.resolution_notes = "Closed by customer confirmation via email."
            ticket.closed_by        = "Customer"
            db.commit()

            return HTMLResponse(f"""
            <html>
            <head><meta charset="UTF-8">
            <title>Ticket Confirmed — ResolveNow AI</title></head>
            <body style="font-family:'Segoe UI',Arial,sans-serif;background:#F8FAFC;
                         display:flex;align-items:center;justify-content:center;
                         height:100vh;margin:0;">
              <div style="text-align:center;padding:2.5rem 3rem;background:#fff;
                          border-radius:16px;border:1px solid #E2E8F0;max-width:440px;
                          box-shadow:0 4px 24px rgba(0,0,0,0.06);">
                <div style="font-size:56px;margin-bottom:1rem;">✅</div>
                <h2 style="color:#15803D;font-size:22px;margin-bottom:.5rem;">
                  Issue Resolved!</h2>
                <p style="color:#6B7280;font-size:13px;line-height:1.7;margin-bottom:1.5rem;">
                  Thank you for confirming. Your ticket
                  <strong style="color:#2563EB;font-family:monospace;">{ticket_id}</strong>
                  has been automatically closed.
                </p>
                <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
                             padding:14px;margin-bottom:1.5rem;">
                  <div style="font-size:13px;color:#166534;">
                    Topic: <strong>{ticket.topic}</strong><br>
                    Status: <strong style="color:#15803D;">Closed</strong><br>
                    Closed by: <strong>Customer Confirmation</strong>
                  </div>
                </div>
                <p style="font-size:11px;color:#9CA3AF;margin:0;">
                  You can safely close this browser tab.
                </p>
              </div>
            </body></html>
            """)

        # ── USER SAYS: STILL HAVING ISSUE ─────────────────────
        else:
            ticket.status           = "In Progress"
            ticket.resolution_notes = "Customer indicated issue not resolved. Escalated to agent."
            db.commit()

            # Send escalation email to assigned agent
            assignee_email = ticket.assigned_email or ""
            assignee_name  = ticket.assigned_to    or "Support Team"
            agent_group    = ticket.assigned_group  or "Support Team"

            if not assignee_email:
                assignee_email = os.getenv("FALLBACK_AGENT_EMAIL", "")

            if assignee_email:
                send_escalation_email(
                    to_email       = assignee_email,
                    ticket_id      = ticket_id,
                    topic          = ticket.topic,
                    agent_group    = agent_group,
                    agent_name     = assignee_name,
                    created_by     = ticket.created_by,
                    solution_tried = ""
                )
                print(f"  ✅ Escalation email sent to {assignee_email}")

            return HTMLResponse(f"""
            <html>
            <head><meta charset="UTF-8">
            <title>Ticket Escalated — ResolveNow AI</title></head>
            <body style="font-family:'Segoe UI',Arial,sans-serif;background:#F8FAFC;
                         display:flex;align-items:center;justify-content:center;
                         height:100vh;margin:0;">
              <div style="text-align:center;padding:2.5rem 3rem;background:#fff;
                          border-radius:16px;border:1px solid #E2E8F0;max-width:440px;
                          box-shadow:0 4px 24px rgba(0,0,0,0.06);">
                <div style="font-size:56px;margin-bottom:1rem;">👤</div>
                <h2 style="color:#D97706;font-size:22px;margin-bottom:.5rem;">
                  Escalated to Agent</h2>
                <p style="color:#6B7280;font-size:13px;line-height:1.7;margin-bottom:1.5rem;">
                  We have noted that the solution did not resolve your issue.
                  Ticket <strong style="color:#2563EB;font-family:monospace;">{ticket_id}</strong>
                  has been escalated to a human agent who will contact you shortly.
                </p>
                <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;
                             padding:14px;">
                  <div style="font-size:13px;color:#92400E;">
                    Topic: <strong>{ticket.topic}</strong><br>
                    Status: <strong style="color:#D97706;">In Progress</strong><br>
                    Assigned to: <strong>{agent_group}</strong>
                  </div>
                </div>
                <p style="font-size:11px;color:#9CA3AF;margin-top:1rem;">
                  You can safely close this browser tab.
                </p>
              </div>
            </body></html>
            """)
    finally:
        db.close()


@app.get("/tickets/{ticket_id}/agent-resolve", response_class=HTMLResponse)
def agent_resolve_ticket(ticket_id: str, status: str = "resolved"):
    """
    Agent clicks email link to update ticket status.
    status=resolved      → marks ticket Resolved in DB
    status=investigating → keeps In Progress
    """
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()

        if not ticket:
            return HTMLResponse(
                f"<h2>Ticket {ticket_id} not found.</h2>",
                status_code=404
            )

        if status == "resolved":
            ticket.status        = "Resolved"
            ticket.resolved_time = datetime.now().isoformat()
            ticket.closed_by     = "Agent"
            db.commit()

            status_label = "Resolved"
            status_color = "#15803D"
            bg_color     = "#F0FDF4"
            border_color = "#BBF7D0"
            text_color   = "#166534"
            icon         = "✅"
            heading      = "Ticket Resolved"
            body_msg     = "You have marked this ticket as resolved. The customer will be notified."

        else:
            ticket.status = "In Progress"
            db.commit()

            status_label = "In Progress"
            status_color = "#D97706"
            bg_color     = "#FFF7ED"
            border_color = "#FED7AA"
            text_color   = "#92400E"
            icon         = "🔍"
            heading      = "Still Investigating"
            body_msg     = "Ticket status updated to In Progress. Continue working on this issue."

        return HTMLResponse(f"""
        <html>
        <head><meta charset="UTF-8">
        <title>{heading} — ResolveNow AI</title></head>
        <body style="font-family:'Segoe UI',Arial,sans-serif;background:#F8FAFC;
                     display:flex;align-items:center;justify-content:center;
                     height:100vh;margin:0;">
          <div style="text-align:center;padding:2.5rem 3rem;background:#fff;
                      border-radius:16px;border:1px solid #E2E8F0;max-width:440px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.06);">
            <div style="font-size:56px;margin-bottom:1rem;">{icon}</div>
            <h2 style="color:{status_color};font-size:22px;margin-bottom:.5rem;">
              {heading}</h2>
            <p style="color:#6B7280;font-size:13px;line-height:1.7;margin-bottom:1.5rem;">
              {body_msg}
            </p>
            <div style="background:{bg_color};border:1px solid {border_color};
                         border-radius:10px;padding:14px;">
              <div style="font-size:13px;color:{text_color};">
                Ticket: <strong style="color:#2563EB;font-family:monospace;">
                {ticket_id}</strong><br>
                Topic: <strong>{ticket.topic}</strong><br>
                Status: <strong style="color:{status_color};">{status_label}</strong>
              </div>
            </div>
            <p style="font-size:11px;color:#9CA3AF;margin-top:1rem;">
              You can safely close this browser tab.
            </p>
          </div>
        </body></html>
        """)
    finally:
        db.close()


@app.get("/tickets")
def get_all_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    db = SessionLocal()

    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)

    if priority:
        query = query.filter(Ticket.priority == priority)

    tickets = query.all()

    result = []

    for t in tickets:
        result.append({
            "ticket_id": t.ticket_id,
            "topic": t.topic,
            "description": t.description,
            "predicted_priority": t.priority,
            "status": t.status,
            "created_by": t.created_by,
            "user_email": t.user_email,
            "assigned_to": t.assigned_to,
            "assigned_group": t.assigned_group,
            "created_time": t.created_time
        })

    return {
        "total": len(result),
        "tickets": sorted(
            result,
            key=lambda x: x["created_time"],
            reverse=True
        )
    }


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):

    db = SessionLocal()

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} not found"
        )

    return {
        "ticket_id": ticket.ticket_id,
        "topic": ticket.topic,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
        "created_by": ticket.created_by,
        "user_email": ticket.user_email,
        "assigned_to": ticket.assigned_to,
        "assigned_group": ticket.assigned_group,
        "created_time": ticket.created_time
    }


@app.put("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, update: TicketUpdate):
    """Manually resolve a ticket from dashboard."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        ticket.status           = update.status
        ticket.resolution_notes = update.resolution_notes
        ticket.assigned_to      = update.agent_name or ticket.assigned_to
        ticket.resolved_time    = datetime.now().isoformat()
        db.commit()
        return {"success": True, "ticket_id": ticket_id, "status": update.status}
    finally:
        db.close()


@app.delete("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str):
    """Close a ticket from dashboard."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        ticket.status     = "Closed"
        ticket.close_time = datetime.now().isoformat()
        db.commit()
        return {"success": True, "message": f"Ticket {ticket_id} closed."}
    finally:
        db.close()


@app.get("/kedb")
def get_kedb():
    """Get all known error database entries."""
    return {"total_known_issues": len(KEDB), "kedb": list(KEDB.values())}


@app.get("/kedb/{topic}")
def get_kedb_entry(topic: str):
    """Check if a topic is a known issue."""
    entry = check_kedb(topic)
    if not entry:
        return {"known_issue": False, "topic": topic}
    return {"known_issue": True, "entry": entry}


@app.get("/analytics/summary")
def get_summary():
    """Dashboard analytics summary from database."""
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).all()
        if not tickets:
            return {"message": "No tickets yet"}

        total         = len(tickets)
        auto_closed   = len([t for t in tickets if t.status == "Closed"])
        human_needed  = len([t for t in tickets if t.priority in ["High", "Critical"]])

        by_priority = {}
        by_status   = {}
        for t in tickets:
            p = t.priority or "Unknown"
            s = t.status   or "Unknown"
            by_priority[p] = by_priority.get(p, 0) + 1
            by_status[s]   = by_status.get(s, 0) + 1

        return {
            "total_tickets":        total,
            "auto_resolved_closed": auto_closed,
            "requires_human":       human_needed,
            "automation_rate":      round(auto_closed / total * 100, 1) if total else 0,
            "by_priority":          by_priority,
            "by_status":            by_status,
            "kedb_size":            len(KEDB)
        }
    finally:
        db.close()


@app.get("/predict")
def predict_only(topic: str, source: str = "Email", product_group: str = "Cloud"):
    """Just predict — do not create ticket."""
    if not MODELS_READY:
        raise HTTPException(status_code=503, detail="Models not ready")
    result     = predict_priority_and_topic(topic, source, product_group, "General Support")
    kedb_entry = check_kedb(topic)
    result["known_issue"]         = kedb_entry is not None
    result["kedb_match"]          = kedb_entry["topic"] if kedb_entry else None
    result["solution_suggestion"] = kedb_entry["solution_suggestion"] if kedb_entry else None
    return result

@app.get("/tickets/{ticket_id}/sla")
def get_ticket_sla(ticket_id: str):
    """
    Get live SLA status for a specific ticket.
    Recalculates breaches in real-time based on current time.
    """
    if ticket_id not in TICKETS:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    ticket = TICKETS[ticket_id]
    sla    = check_sla_status(ticket)   # Live recalculation
    TICKETS[ticket_id]["sla"] = sla     # Update stored status

    cfg = ticket.get("sla", {})
    response_remaining    = get_sla_remaining(cfg["response_deadline"])    if cfg.get("response_deadline")    else {}
    restoration_remaining = get_sla_remaining(cfg["restoration_deadline"]) if cfg.get("restoration_deadline") else {}

    return {
        "ticket_id":              ticket_id,
        "priority":               ticket.get("predicted_priority"),
        "sla":                    sla,
        "response_remaining":     response_remaining,
        "restoration_remaining":  restoration_remaining,
    }


@app.get("/sla/breached")
def get_breached_tickets():

    db = SessionLocal()

    try:

        breached = []
        warnings = []

        tickets = db.query(Ticket).all()

        for ticket in tickets:

            ticket_data = {
                "ticket_id": ticket.ticket_id,
                "topic": ticket.topic,
                "status": ticket.status,
                "predicted_priority": ticket.priority,
                "created_time": ticket.created_time,
                "assigned_to": ticket.assigned_to,
                "agent_group": ticket.assigned_group,
                "created_by": ticket.created_by,
                "user_email": ticket.user_email
            }

            # Create SLA if missing
            ticket_data["sla"] = calculate_sla_deadlines(
                created_time=ticket.created_time,
                priority=ticket.priority
            )

            updated_sla = check_sla_status(ticket_data)

            # -------------------------
            # Breached Tickets
            # -------------------------
            if (
                updated_sla.get("response_breached")
                or updated_sla.get("restoration_breached")
            ):

                breached.append({
                    "ticket_id": ticket.ticket_id,
                    "topic": ticket.topic,
                    "priority": ticket.priority,
                    "status": ticket.status,
                    "response_sla_status":
                        updated_sla.get("response_sla_status"),
                    "restoration_sla_status":
                        updated_sla.get("restoration_sla_status"),
                    "response_deadline":
                        updated_sla.get("response_deadline"),
                    "restoration_deadline":
                        updated_sla.get("restoration_deadline")
                })

            # -------------------------
            # Warning Tickets
            # -------------------------
            warn = get_sla_warning_status(ticket_data)

            if (
                warn.get("response_warning")
                and not updated_sla.get("response_breached")
            ):

                warnings.append({
                    "ticket_id": ticket.ticket_id,
                    "topic": ticket.topic,
                    "priority": ticket.priority,
                    "sla_type": "Response",
                    "percent_used":
                        warn.get("response_percent"),
                    "deadline":
                        updated_sla.get("response_deadline")
                })

            if (
                warn.get("restoration_warning")
                and not updated_sla.get("restoration_breached")
            ):

                warnings.append({
                    "ticket_id": ticket.ticket_id,
                    "topic": ticket.topic,
                    "priority": ticket.priority,
                    "sla_type": "Restoration",
                    "percent_used":
                        warn.get("restoration_percent"),
                    "deadline":
                        updated_sla.get("restoration_deadline")
                })

        return {
            "total_breached": len(breached),
            "total_warnings": len(warnings),
            "breached_tickets": breached,
            "warning_tickets": warnings
        }

    finally:
        db.close()
