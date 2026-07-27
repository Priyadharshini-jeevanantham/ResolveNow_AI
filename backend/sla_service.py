# backend/sla_service.py
# SLA definitions, tracking, and breach detection

from datetime import datetime, timedelta
from typing import Optional

# ── SLA DEFINITIONS ───────────────────────────────────────
SLA_CONFIG = {
    "Critical": {
        "response_hours":     2,
        "restoration_hours":  24,
        "label":              "Critical SLA"
    },
    "High": {
        "response_hours":     2,
        "restoration_hours":  24,
        "label":              "High SLA"
    },
    "Medium": {
        "response_hours":     24,
        "restoration_hours":  96,   # 4 business days = 4 × 24h (simplified)
        "label":              "Medium SLA"
    },
    "Low": {
        "response_hours":     24,
        "restoration_hours":  96,
        "label":              "Low SLA"
    }
}


def get_sla_config(priority: str) -> dict:
    """Return SLA config for a given priority."""
    return SLA_CONFIG.get(priority, SLA_CONFIG["Low"])


def calculate_sla_deadlines(created_time: str, priority: str) -> dict:
    """
    Calculate response and restoration deadline timestamps
    from ticket creation time.
    """
    cfg = get_sla_config(priority)
    created_dt = datetime.fromisoformat(created_time)

    response_deadline    = created_dt + timedelta(hours=cfg["response_hours"])
    restoration_deadline = created_dt + timedelta(hours=cfg["restoration_hours"])

    return {
        "response_deadline":        response_deadline.isoformat(),
        "restoration_deadline":     restoration_deadline.isoformat(),
        "response_hours_allowed":   cfg["response_hours"],
        "restoration_hours_allowed":cfg["restoration_hours"],
        "response_sla_status":      "Active",    # Active / Met / Breached
        "restoration_sla_status":   "Active",
        "response_met_at":          None,
        "restoration_met_at":       None,
        "response_breached":        False,
        "restoration_breached":     False
    }


def check_sla_status(ticket: dict) -> dict:
    """
    Re-evaluate SLA status for a ticket RIGHT NOW.
    Called every time /sla/breached is hit.
    """
    sla = ticket.get("sla", {})
    if not sla:
        return sla

    now = datetime.now()

    # ── RESPONSE SLA ──────────────────────────────────────
    # Response SLA = ticket must be ASSIGNED within allowed hours
    # Only skip if already confirmed Met with a valid assigned_at timestamp
    response_deadline = datetime.fromisoformat(sla["response_deadline"])
    assigned_at_str   = ticket.get("assigned_at")

    if assigned_at_str:
        assigned_at = datetime.fromisoformat(assigned_at_str)
        if assigned_at <= response_deadline:
            sla["response_sla_status"] = "Met"
            sla["response_met_at"]     = assigned_at_str
            sla["response_breached"]   = False
        else:
            # Assigned late — still a breach
            sla["response_sla_status"] = "Breached"
            sla["response_breached"]   = True
    else:
        # Not yet assigned — check if deadline has passed
        if now > response_deadline:
            sla["response_sla_status"] = "Breached"
            sla["response_breached"]   = True
        else:
            sla["response_sla_status"] = "Active"
            sla["response_breached"]   = False

    # ── RESTORATION SLA ───────────────────────────────────
    # Restoration SLA = ticket must be Resolved/Closed within allowed hours
    restoration_deadline = datetime.fromisoformat(sla["restoration_deadline"])
    resolved_at_str      = ticket.get("resolved_time") or ticket.get("close_time")

    if resolved_at_str:
        resolved_at = datetime.fromisoformat(resolved_at_str)
        if resolved_at <= restoration_deadline:
            sla["restoration_sla_status"] = "Met"
            sla["restoration_met_at"]     = resolved_at_str
            sla["restoration_breached"]   = False
        else:
            sla["restoration_sla_status"] = "Breached"
            sla["restoration_breached"]   = True
    else:
        # Not yet resolved — check if deadline has passed
        if now > restoration_deadline:
            sla["restoration_sla_status"] = "Breached"
            sla["restoration_breached"]   = True
        else:
            sla["restoration_sla_status"] = "Active"
            sla["restoration_breached"]   = False
    # ── Preserve warning email sent flags ──
    # (don't reset them on re-evaluation)
    if "warning_email_sent_response" not in sla:
        sla["warning_email_sent_response"] = False
    if "warning_email_sent_restoration" not in sla:
        sla["warning_email_sent_restoration"] = False

    return sla


def get_sla_remaining(deadline_iso: str) -> dict:
    """
    Calculate time remaining until an SLA deadline.
    Returns hours, minutes, and a human-readable string.
    """
    deadline = datetime.fromisoformat(deadline_iso)
    now      = datetime.now()
    delta    = deadline - now

    if delta.total_seconds() <= 0:
        return {"hours": 0, "minutes": 0, "label": "Breached", "overdue_by": abs(int(delta.total_seconds() // 3600))}

    total_minutes = int(delta.total_seconds() // 60)
    hours         = total_minutes // 60
    minutes       = total_minutes % 60

    if hours >= 24:
        days = hours // 24
        label = f"{days}d {hours % 24}h remaining"
    elif hours > 0:
        label = f"{hours}h {minutes}m remaining"
    else:
        label = f"{minutes}m remaining"

    return {"hours": hours, "minutes": minutes, "label": label, "overdue_by": 0}
def get_sla_warning_status(ticket: dict) -> dict:
    """
    Check if ticket is at 75% of SLA time used.
    Returns warning flags for response and restoration SLA.
    """
    sla = ticket.get("sla", {})
    if not sla:
        return {"response_warning": False, "restoration_warning": False}

    now = datetime.now()
    created_time = datetime.fromisoformat(ticket.get("created_time", now.isoformat()))

    result = {
        "response_warning":     False,
        "restoration_warning":  False,
        "response_percent":     0,
        "restoration_percent":  0,
        "warning_email_sent_response":    sla.get("warning_email_sent_response", False),
        "warning_email_sent_restoration": sla.get("warning_email_sent_restoration", False),
    }

    # ── RESPONSE SLA WARNING ──────────────────────────────
    if sla.get("response_sla_status") == "Active":
        response_deadline  = datetime.fromisoformat(sla["response_deadline"])
        total_seconds      = (response_deadline - created_time).total_seconds()
        elapsed_seconds    = (now - created_time).total_seconds()
        percent_used       = (elapsed_seconds / total_seconds * 100) if total_seconds > 0 else 0
        result["response_percent"] = round(min(percent_used, 100), 1)

        if percent_used >= 75:
            result["response_warning"] = True

    # ── RESTORATION SLA WARNING ───────────────────────────
    if sla.get("restoration_sla_status") == "Active":
        restoration_deadline = datetime.fromisoformat(sla["restoration_deadline"])
        total_seconds        = (restoration_deadline - created_time).total_seconds()
        elapsed_seconds      = (now - created_time).total_seconds()
        percent_used         = (elapsed_seconds / total_seconds * 100) if total_seconds > 0 else 0
        result["restoration_percent"] = round(min(percent_used, 100), 1)

        if percent_used >= 75:
            result["restoration_warning"] = True

    return result