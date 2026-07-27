# backend/email_service.py
# Handles all outgoing emails for ResolveNow AI

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL    = os.getenv("EMAIL_SENDER", "")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
BASE_URL        = os.getenv("BASE_URL", "http://localhost:8000")


# ──────────────────────────────────────────────────────────────
# 1. LOW / MEDIUM PRIORITY — Known Issue → Email user with solution
#    Includes "✅ Solved" and "❌ Still Having Issue" buttons
# ──────────────────────────────────────────────────────────────
def send_solution_email(
    to_email: str,
    ticket_id: str,
    topic: str,
    solution: str,
    steps: list,
    created_by: str = "User"
) -> dict:
    """
    Send solution email to USER for known low/medium priority issues.
    Buttons:
      • Yes, Issue Resolved  → /tickets/{id}/confirm?resolved=yes  → auto-close ticket
      • Still Having Issue   → /tickets/{id}/confirm?resolved=no   → escalate to assignee
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {"success": False, "message": "Email credentials not configured in .env file"}

    confirm_url = f"{BASE_URL}/tickets/{ticket_id}/confirm?action=close"

    steps_html = "".join([
        f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #1E2D45;vertical-align:top;">
            <span style="background:#3B82F6;color:#fff;border-radius:50%;
                         width:22px;height:22px;display:inline-flex;
                         align-items:center;justify-content:center;
                         font-size:11px;font-weight:700;flex-shrink:0;
                         margin-right:10px;">{i+1}</span>
          </td>
          <td style="padding:8px 0 8px 4px;border-bottom:1px solid #1E2D45;
                     font-size:13px;color:#CBD5E1;line-height:1.6;">
            {step.lstrip('0123456789. ')}
          </td>
        </tr>
        """
        for i, step in enumerate(steps)
    ])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
    </head>
    <body style="margin:0;padding:0;background:#070B14;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 20px;">
            <table width="560" cellpadding="0" cellspacing="0"
                   style="background:#0D1220;border-radius:16px;
                          border:1px solid #1E2D45;overflow:hidden;">

              <!-- HEADER -->
              <tr>
                <td style="background:linear-gradient(135deg,#1E3A5F,#0D1220);
                            padding:28px 32px;border-bottom:1px solid #1E2D45;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <div style="font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px;">
                          ⚡ Resolve<span style="color:#3B82F6;">Now</span> AI
                        </div>
                        <div style="font-size:11px;color:#4A5A78;margin-top:3px;
                                    letter-spacing:1px;text-transform:uppercase;">
                          ITSM Automated Support
                        </div>
                      </td>
                      <td align="right">
                        <span style="background:#10B981;color:#fff;font-size:10px;
                                     padding:4px 12px;border-radius:20px;font-weight:600;">
                          SOLUTION FOUND
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- TICKET BADGE -->
              <tr>
                <td style="padding:24px 32px 0;">
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="background:#141928;border:1px solid #1E2D45;
                                  border-radius:8px;padding:8px 14px;">
                        <span style="font-size:11px;color:#4A5A78;font-family:monospace;">TICKET ID</span>
                        <span style="font-size:13px;color:#3B82F6;font-weight:700;
                                     margin-left:10px;font-family:monospace;">{ticket_id}</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- GREETING -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <p style="font-size:15px;color:#E2E8F6;font-weight:600;margin:0 0 6px;">
                    Hi {created_by},
                  </p>
                  <p style="font-size:13px;color:#8A9BBE;line-height:1.7;margin:0;">
                    Our AI system has identified a known solution for your
                    <strong style="color:#E2E8F6;">{topic}</strong> issue.
                    Please follow the steps below to resolve it.
                  </p>
                </td>
              </tr>

              <!-- SOLUTION BOX -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="background:#141928;border:1px solid #1E2D45;
                               border-left:3px solid #10B981;border-radius:10px;
                               padding:16px 18px;">
                    <div style="font-size:10px;color:#10B981;text-transform:uppercase;
                                 letter-spacing:1px;font-weight:600;margin-bottom:8px;">
                      💡 Solution Summary
                    </div>
                    <div style="font-size:13px;color:#CBD5E1;line-height:1.65;">
                      {solution}
                    </div>
                  </div>
                </td>
              </tr>

              <!-- STEPS -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="font-size:11px;color:#4A5A78;text-transform:uppercase;
                               letter-spacing:1px;font-weight:600;margin-bottom:10px;">
                    📋 Step-by-Step Resolution
                  </div>
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background:#141928;border:1px solid #1E2D45;
                                border-radius:10px;overflow:hidden;">
                    {steps_html}
                  </table>
                </td>
              </tr>

              <!-- CONFIRMATION BUTTONS -->
              <tr>
                <td style="padding:24px 32px 0;">
                  <div style="background:#0D2137;border:1px solid #1E3A5F;
                               border-radius:10px;padding:18px;text-align:center;">
                    <div style="font-size:13px;color:#8A9BBE;margin-bottom:14px;">
                      Did this solution resolve your issue?
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="padding:0 6px;">
                          <a href="{confirm_url}&resolved=yes"
                             style="display:inline-block;background:#10B981;color:#fff;
                                    font-size:13px;font-weight:700;padding:11px 28px;
                                    border-radius:8px;text-decoration:none;letter-spacing:.3px;">
                            ✅ Yes, Issue Resolved
                          </a>
                        </td>
                        <td align="center" style="padding:0 6px;">
                          <a href="{confirm_url}&resolved=no"
                             style="display:inline-block;background:#1C2438;color:#8A9BBE;
                                    font-size:13px;font-weight:600;padding:11px 28px;
                                    border-radius:8px;text-decoration:none;border:1px solid #1E2D45;">
                            ❌ Still Having Issue
                          </a>
                        </td>
                      </tr>
                    </table>
                    <div style="font-size:11px;color:#4A5A78;margin-top:12px;">
                      Clicking "Yes" will automatically close your ticket.<br>
                      Clicking "Still Having Issue" will escalate to a human agent.
                    </div>
                  </div>
                </td>
              </tr>

              <!-- FOOTER -->
              <tr>
                <td style="padding:24px 32px;border-top:1px solid #1E2D45;margin-top:24px;">
                  <p style="font-size:11px;color:#4A5A78;text-align:center;margin:0;line-height:1.7;">
                    This is an automated message from ResolveNow AI.<br>
                    Ticket <span style="color:#3B82F6;font-family:monospace;">{ticket_id}</span>
                    is currently <strong style="color:#F59E0B;">Pending Customer</strong> response.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    plain = f"""
Hi {created_by},

ResolveNow AI has found a solution for your {topic} issue.
Ticket ID: {ticket_id}

SOLUTION:
{solution}

STEPS:
{chr(10).join(steps)}

✅ Resolved? Click here: {confirm_url}&resolved=yes
❌ Still having issue? Click here: {confirm_url}&resolved=no

ResolveNow AI — Automated ITSM Support
    """.strip()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{ticket_id}] Solution Found — {topic} | ResolveNow AI"
        msg["From"]    = f"ResolveNow AI <{SENDER_EMAIL}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"  ✅ Solution email sent to {to_email} for {ticket_id}")
        return {"success": True, "message": f"Solution email sent to {to_email}", "email_sent_to": to_email}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Gmail authentication failed. Check EMAIL_SENDER and EMAIL_PASSWORD in .env"}
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}


# ──────────────────────────────────────────────────────────────
# 2. HIGH / CRITICAL PRIORITY → Email ASSIGNEE
#    Known issue  → includes solution suggestion for agent
#    Unknown issue → urgent alert, investigation required
# ──────────────────────────────────────────────────────────────
def send_high_priority_email(
    to_email: str,
    ticket_id: str,
    topic: str,
    priority: str,
    solution: str = None,
    steps: list = None,
    is_known: bool = False,
    agent_group: str = "Support Team",
    agent_name: str = "",
    created_by: str = "User",
    description: str = "",
    is_user_ack: bool = False,
    sla_info: dict = None
) -> dict:
    """
    Send high priority alert email to the ASSIGNEE (agent/team).
    If known issue  → includes solution suggestion (agent must verify before closing).
    If unknown issue → urgent investigation alert only.
    """

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {"success": False, "message": "Email credentials not configured in .env"}

    priority_color = "#EF4444" if priority.lower() == "critical" else "#F59E0B"
    priority_label = priority.upper()
    steps = steps or []

    # ── SLA row (built first, used inside HTML template below) ──
    sla_row = ""
    if sla_info:
        sla_row = f"""
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">SLA Deadlines</td>
                      <td style="padding:10px 14px;font-size:12px;">
                        <span style="color:#F59E0B;">⏱ Response by: {sla_info.get('response_deadline','—')[:16].replace('T',' ')}</span><br>
                        <span style="color:#EF4444;">🔧 Restore by: {sla_info.get('restoration_deadline','—')[:16].replace('T',' ')}</span>
                      </td>
                    </tr>"""

    # ── Solution block (known issues only) ──
    if is_user_ack:
        solution_block = ""
    elif is_known and solution:
        steps_html = "".join([
            f"""<tr>
              <td style="padding:7px 0;border-bottom:1px solid #1E2D45;vertical-align:top;">
                <span style="background:#F59E0B;color:#000;border-radius:50%;
                             width:22px;height:22px;display:inline-flex;
                             align-items:center;justify-content:center;
                             font-size:11px;font-weight:700;margin-right:10px;">{i+1}</span>
              </td>
              <td style="padding:7px 0 7px 4px;border-bottom:1px solid #1E2D45;
                         font-size:13px;color:#CBD5E1;line-height:1.6;">
                {step.lstrip('0123456789. ')}
              </td>
            </tr>"""
            for i, step in enumerate(steps)
        ])

        solution_block = f"""
        <tr>
          <td style="padding:20px 32px 0;">
            <div style="background:#1C1A00;border:1px solid #3D3400;
                         border-left:3px solid #F59E0B;border-radius:10px;padding:16px 18px;">
              <div style="font-size:10px;color:#F59E0B;text-transform:uppercase;
                           letter-spacing:1px;font-weight:600;margin-bottom:8px;">
                💡 Known Issue — Suggested Solution
              </div>
              <div style="font-size:13px;color:#CBD5E1;line-height:1.65;margin-bottom:12px;">
                {solution}
              </div>
              <div style="font-size:11px;color:#6B7280;margin-bottom:8px;
                           text-transform:uppercase;letter-spacing:.8px;">Resolution Steps</div>
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#141928;border:1px solid #1E2D45;
                            border-radius:8px;overflow:hidden;padding:0 12px;">
                {steps_html}
              </table>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:12px 32px 0;">
            <div style="background:#1A0A0A;border:1px solid #3D1515;border-radius:8px;padding:12px 14px;">
              <div style="font-size:12px;color:#FCA5A5;line-height:1.6;">
                ⚠️ <strong>Important:</strong> This is a HIGH PRIORITY ticket.
                Even though a solution is suggested, <strong>you must evaluate
                and confirm the resolution manually.</strong>
                Do not auto-close without verifying with the user.
              </div>
            </div>
          </td>
        </tr>"""
    else:
        solution_block = """
        <tr>
          <td style="padding:20px 32px 0;">
            <div style="background:#1A0A0A;border:1px solid #3D1515;
                         border-left:3px solid #EF4444;border-radius:10px;padding:16px 18px;">
              <div style="font-size:10px;color:#EF4444;text-transform:uppercase;
                           letter-spacing:1px;font-weight:600;margin-bottom:8px;">
                🔍 Unknown Issue — Investigation Required
              </div>
              <div style="font-size:13px;color:#CBD5E1;line-height:1.65;">
                This issue has not been seen before and has no known solution.
                <strong style="color:#FCA5A5;">Immediate investigation is required.</strong>
                Please contact the user directly and begin root cause analysis.
              </div>
            </div>
          </td>
        </tr>"""

    description_block = f"""
    <tr>
      <td style="padding:16px 32px 0;">
        <div style="font-size:11px;color:#4A5A78;text-transform:uppercase;
                     letter-spacing:1px;margin-bottom:6px;">Issue Description</div>
        <div style="background:#141928;border:1px solid #1E2D45;border-radius:8px;
                     padding:12px 14px;font-size:13px;color:#8A9BBE;line-height:1.6;">
          {description or 'No description provided.'}
        </div>
      </td>
    </tr>""" if description else ""

    assignee_display = agent_name if agent_name else agent_group

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#070B14;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 20px;">
            <table width="560" cellpadding="0" cellspacing="0"
                   style="background:#0D1220;border-radius:16px;
                          border:2px solid {priority_color};overflow:hidden;">

              <!-- URGENT BANNER -->
              <tr>
                <td style="background:{priority_color};padding:10px 32px;text-align:center;">
                  <div style="font-size:13px;font-weight:800;color:#fff;letter-spacing:1px;">
                    🚨 {priority_label} PRIORITY — IMMEDIATE ACTION REQUIRED
                  </div>
                </td>
              </tr>

              <!-- HEADER -->
              <tr>
                <td style="background:linear-gradient(135deg,#1A0A0A,#0D1220);
                            padding:24px 32px;border-bottom:1px solid #1E2D45;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <div style="font-size:20px;font-weight:800;color:#fff;">
                          ⚡ Resolve<span style="color:#3B82F6;">Now</span> AI
                        </div>
                        <div style="font-size:11px;color:#4A5A78;margin-top:3px;
                                     letter-spacing:1px;text-transform:uppercase;">
                          High Priority Alert System
                        </div>
                      </td>
                      <td align="right">
                        <span style="background:{priority_color};color:#fff;font-size:11px;
                                     padding:5px 14px;border-radius:20px;font-weight:700;">
                          {priority_label}
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- TICKET INFO -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="font-size:14px;font-weight:600;color:#E2E8F6;margin-bottom:12px;">
                    Dear {assignee_display},
                  </div>
                  <p style="font-size:13px;color:#8A9BBE;line-height:1.7;margin:0;">
                    A <strong style="color:{priority_color};">{priority_label} PRIORITY</strong>
                    ticket has been assigned to you and requires
                    <strong style="color:#E2E8F6;">immediate attention.</strong>
                  </p>
                </td>
              </tr>

              <!-- TICKET DETAILS TABLE -->
              <tr>
                <td style="padding:16px 32px 0;">
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background:#141928;border:1px solid #1E2D45;
                                border-radius:10px;overflow:hidden;">
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  width:140px;text-transform:uppercase;letter-spacing:.7px;">Ticket ID</td>
                      <td style="padding:10px 14px;font-size:13px;color:#3B82F6;
                                  font-family:monospace;font-weight:700;">{ticket_id}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Issue Type</td>
                      <td style="padding:10px 14px;font-size:13px;color:#E2E8F6;font-weight:600;">{topic}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Priority</td>
                      <td style="padding:10px 14px;">
                        <span style="background:{priority_color}22;color:{priority_color};font-size:12px;
                                     padding:3px 10px;border-radius:20px;font-weight:700;
                                     border:1px solid {priority_color}44;">
                          {priority_label}
                        </span>
                      </td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Reported By</td>
                      <td style="padding:10px 14px;font-size:13px;color:#E2E8F6;">{created_by}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Known Issue</td>
                      <td style="padding:10px 14px;font-size:13px;
                                  color:{'#10B981' if is_known else '#EF4444'};">
                        {'✅ Yes — solution suggested below' if is_known else '❌ No — investigation needed'}
                      </td>
                    </tr>
                    {sla_row}
                  </table>
                </td>
              </tr>

              {description_block}
              {solution_block}

              <!-- ACTION BUTTONS -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="background:#0D1F35;border:1px solid #1E3A5F;
                               border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:#8A9BBE;margin-bottom:12px;">
                      Update this ticket after resolution
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved"
                             style="display:inline-block;background:#10B981;color:#fff;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            ✅ Mark Resolved
                          </a>
                        </td>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating"
                             style="display:inline-block;background:#F59E0B;color:#000;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            🔍 Still Investigating
                          </a>
                        </td>
                      </tr>
                    </table>
                  </div>
                </td>
              </tr>

              <!-- FOOTER -->
              <tr>
                <td style="padding:24px 32px;border-top:1px solid #1E2D45;margin-top:20px;">
                  <p style="font-size:11px;color:#4A5A78;text-align:center;margin:0;line-height:1.7;">
                    This is an automated high priority alert from ResolveNow AI.<br>
                    Ticket <span style="color:#3B82F6;font-family:monospace;">{ticket_id}</span>
                    — Please respond within SLA timeframe.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    plain = f"""
🚨 {priority_label} PRIORITY ALERT — ResolveNow AI

Assigned To : {assignee_display}
Ticket ID   : {ticket_id}
Issue       : {topic}
Priority    : {priority_label}
Reported By : {created_by}
Known Issue : {'Yes' if is_known else 'No'}

{f'SUGGESTED SOLUTION: {solution}' if solution else 'No known solution — investigation required.'}

Description: {description or 'None provided'}

✅ Mark Resolved      : {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved
🔍 Still Investigating: {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating
    """.strip()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 [{priority_label}] {ticket_id} — {topic} | Immediate Action Required"
        msg["From"]    = f"ResolveNow AI <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg["X-Priority"] = "1"
        msg["Importance"] = "High"

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"  ✅ High priority email sent to {to_email} for {ticket_id}")
        return {"success": True, "message": f"High priority email sent to {to_email}", "sent_to": to_email}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Gmail authentication failed"}
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}
# ──────────────────────────────────────────────────────────────
# 3. ESCALATION EMAIL → When user clicks "Still Having Issue"
#    Sends alert to the ASSIGNEE that the self-service solution failed
# ──────────────────────────────────────────────────────────────
def send_escalation_email(
    to_email: str,
    ticket_id: str,
    topic: str,
    agent_group: str = "Support Team",
    agent_name: str = "",
    created_by: str = "User",
    solution_tried: str = ""
) -> dict:
    """
    Sent to the ASSIGNEE when the user clicks 'Still Having Issue'.
    Notifies the agent that the automated solution did not work and
    they need to take over the ticket.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {"success": False, "message": "Email credentials not configured in .env"}

    assignee_display = agent_name if agent_name else agent_group

    solution_tried_block = f"""
    <tr>
      <td style="padding:16px 32px 0;">
        <div style="font-size:11px;color:#4A5A78;text-transform:uppercase;
                     letter-spacing:1px;margin-bottom:6px;">Solution Already Tried (Did Not Work)</div>
        <div style="background:#1A0A0A;border:1px solid #3D1515;border-radius:8px;
                     padding:12px 14px;font-size:13px;color:#FCA5A5;line-height:1.6;">
          {solution_tried}
        </div>
      </td>
    </tr>""" if solution_tried else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#070B14;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 20px;">
            <table width="560" cellpadding="0" cellspacing="0"
                   style="background:#0D1220;border-radius:16px;
                          border:2px solid #F59E0B;overflow:hidden;">

              <!-- BANNER -->
              <tr>
                <td style="background:#F59E0B;padding:10px 32px;text-align:center;">
                  <div style="font-size:13px;font-weight:800;color:#000;letter-spacing:1px;">
                    ⚠️ CUSTOMER ESCALATION — SELF-SERVICE SOLUTION DID NOT WORK
                  </div>
                </td>
              </tr>

              <!-- HEADER -->
              <tr>
                <td style="background:linear-gradient(135deg,#1C1500,#0D1220);
                            padding:24px 32px;border-bottom:1px solid #1E2D45;">
                  <div style="font-size:20px;font-weight:800;color:#fff;">
                    ⚡ Resolve<span style="color:#3B82F6;">Now</span> AI
                  </div>
                  <div style="font-size:11px;color:#4A5A78;margin-top:3px;
                               letter-spacing:1px;text-transform:uppercase;">
                    Escalation Alert
                  </div>
                </td>
              </tr>

              <!-- MESSAGE -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="font-size:14px;font-weight:600;color:#E2E8F6;margin-bottom:10px;">
                    Dear {assignee_display},
                  </div>
                  <p style="font-size:13px;color:#8A9BBE;line-height:1.7;margin:0;">
                    The customer <strong style="color:#E2E8F6;">{created_by}</strong>
                    has indicated that the automated solution sent for ticket
                    <strong style="color:#3B82F6;font-family:monospace;">{ticket_id}</strong>
                    did <strong style="color:#EF4444;">not resolve</strong> their issue.
                    Please take over and contact the customer directly.
                  </p>
                </td>
              </tr>

              <!-- TICKET DETAILS -->
              <tr>
                <td style="padding:16px 32px 0;">
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background:#141928;border:1px solid #1E2D45;
                                border-radius:10px;overflow:hidden;">
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  width:140px;text-transform:uppercase;letter-spacing:.7px;">Ticket ID</td>
                      <td style="padding:10px 14px;font-size:13px;color:#3B82F6;
                                  font-family:monospace;font-weight:700;">{ticket_id}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Issue</td>
                      <td style="padding:10px 14px;font-size:13px;color:#E2E8F6;font-weight:600;">{topic}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Reported By</td>
                      <td style="padding:10px 14px;font-size:13px;color:#E2E8F6;">{created_by}</td>
                    </tr>
                    <tr>
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Status</td>
                      <td style="padding:10px 14px;">
                        <span style="background:#F59E0B22;color:#F59E0B;font-size:12px;
                                     padding:3px 10px;border-radius:20px;font-weight:700;
                                     border:1px solid #F59E0B44;">
                          Escalated — In Progress
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              {solution_tried_block}

              <!-- ACTION BUTTONS -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="background:#0D1F35;border:1px solid #1E3A5F;
                               border-radius:10px;padding:16px;text-align:center;">
                    <div style="font-size:12px;color:#8A9BBE;margin-bottom:12px;">
                      Update this ticket after resolution
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved"
                             style="display:inline-block;background:#10B981;color:#fff;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            ✅ Mark Resolved
                          </a>
                        </td>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating"
                             style="display:inline-block;background:#F59E0B;color:#000;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            🔍 Still Investigating
                          </a>
                        </td>
                      </tr>
                    </table>
                  </div>
                </td>
              </tr>

              <!-- FOOTER -->
              <tr>
                <td style="padding:24px 32px;border-top:1px solid #1E2D45;">
                  <p style="font-size:11px;color:#4A5A78;text-align:center;margin:0;line-height:1.7;">
                    Customer escalation from ResolveNow AI.<br>
                    Ticket <span style="color:#3B82F6;font-family:monospace;">{ticket_id}</span>
                    — Please respond within SLA timeframe.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    plain = f"""
⚠️ CUSTOMER ESCALATION — ResolveNow AI

Ticket ID   : {ticket_id}
Issue       : {topic}
Reported By : {created_by}
Assigned To : {assignee_display}
Status      : Escalated — In Progress

The customer indicated the automated solution did NOT resolve their issue.
{f'Solution tried: {solution_tried}' if solution_tried else ''}

Please contact the customer and take over the ticket.

✅ Mark Resolved      : {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved
🔍 Still Investigating: {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating
    """.strip()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚠️ [ESCALATED] {ticket_id} — {topic} | Customer Says Not Resolved"
        msg["From"]    = f"ResolveNow AI <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg["X-Priority"] = "2"

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"  ✅ Escalation email sent to {to_email} for {ticket_id}")
        return {"success": True, "message": f"Escalation email sent to {to_email}", "sent_to": to_email}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Gmail authentication failed"}
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}

# ──────────────────────────────────────────────────────────────────────────────
# 4. SLA WARNING EMAIL → 75% of SLA time used
#    Sent to assignee as early warning before breach
# ──────────────────────────────────────────────────────────────────────────────
def send_sla_warning_email(
    to_email: str,
    ticket_id: str,
    topic: str,
    priority: str,
    sla_type: str,          # "Response" or "Restoration"
    percent_used: float,
    deadline: str,
    agent_name: str = "",
    agent_group: str = "Support Team",
    created_by: str = "User"
) -> dict:
    """
    Warning email sent when 75% of SLA time is consumed.
    Gives assignee early notice before a breach occurs.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return {"success": False, "message": "Email credentials not configured"}

    assignee_display = agent_name if agent_name else agent_group
    deadline_clean   = deadline[:16].replace("T", " ") if deadline else "—"
    remaining_pct    = round(100 - percent_used, 1)
    priority_color   = "#EF4444" if priority.lower() == "critical" else "#F59E0B"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#070B14;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 20px;">
            <table width="560" cellpadding="0" cellspacing="0"
                   style="background:#0D1220;border-radius:16px;
                          border:2px solid #F59E0B;overflow:hidden;">

              <!-- WARNING BANNER -->
              <tr>
                <td style="background:linear-gradient(90deg,#78350F,#92400E);
                            padding:10px 32px;text-align:center;">
                  <div style="font-size:13px;font-weight:800;color:#FDE68A;letter-spacing:1px;">
                    ⚠️ SLA WARNING — 75% TIME CONSUMED — ACTION REQUIRED SOON
                  </div>
                </td>
              </tr>

              <!-- HEADER -->
              <tr>
                <td style="padding:24px 32px;border-bottom:1px solid #1E2D45;">
                  <div style="font-size:20px;font-weight:800;color:#fff;">
                    ⚡ Resolve<span style="color:#3B82F6;">Now</span> AI
                  </div>
                  <div style="font-size:11px;color:#4A5A78;margin-top:3px;
                               letter-spacing:1px;text-transform:uppercase;">
                    SLA Early Warning System
                  </div>
                </td>
              </tr>

              <!-- MESSAGE -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="font-size:14px;font-weight:600;color:#E2E8F6;margin-bottom:10px;">
                    Dear {assignee_display},
                  </div>
                  <p style="font-size:13px;color:#8A9BBE;line-height:1.7;margin:0;">
                    Ticket <strong style="color:#3B82F6;font-family:monospace;">{ticket_id}</strong>
                    has consumed <strong style="color:#F59E0B;">{percent_used}%</strong>
                    of its <strong style="color:#E2E8F6;">{sla_type} SLA</strong> time.
                    You have only <strong style="color:#FCD34D;">{remaining_pct}%</strong>
                    of the allowed time remaining before a breach occurs.
                  </p>
                </td>
              </tr>

              <!-- PROGRESS BAR -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="font-size:10px;color:#4A5A78;text-transform:uppercase;
                               letter-spacing:1px;margin-bottom:8px;font-family:monospace;">
                    {sla_type} SLA Usage
                  </div>
                  <div style="background:#141928;border-radius:6px;height:10px;overflow:hidden;">
                    <div style="width:{percent_used}%;height:10px;
                                background:linear-gradient(90deg,#F59E0B,#EF4444);
                                border-radius:6px;"></div>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                               margin-top:4px;font-size:10px;color:#6B7280;">
                    <span>0%</span>
                    <span style="color:#F59E0B;font-weight:600;">{percent_used}% used</span>
                    <span>100%</span>
                  </div>
                </td>
              </tr>

              <!-- TICKET DETAILS -->
              <tr>
                <td style="padding:16px 32px 0;">
                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="background:#141928;border:1px solid #1E2D45;
                                border-radius:10px;overflow:hidden;">
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  width:140px;text-transform:uppercase;letter-spacing:.7px;">Ticket ID</td>
                      <td style="padding:10px 14px;font-size:13px;color:#3B82F6;
                                  font-family:monospace;font-weight:700;">{ticket_id}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Topic</td>
                      <td style="padding:10px 14px;font-size:13px;color:#E2E8F6;
                                  font-weight:600;">{topic}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Priority</td>
                      <td style="padding:10px 14px;">
                        <span style="background:{priority_color}22;color:{priority_color};
                                     font-size:12px;padding:3px 10px;border-radius:20px;
                                     font-weight:700;border:1px solid {priority_color}44;">
                          {priority.upper()}
                        </span>
                      </td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">SLA Type</td>
                      <td style="padding:10px 14px;font-size:13px;
                                  color:#F59E0B;font-weight:600;">{sla_type} SLA</td>
                    </tr>
                    <tr style="border-bottom:1px solid #1E2D45;">
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Deadline</td>
                      <td style="padding:10px 14px;font-size:13px;
                                  color:#FCD34D;font-weight:600;">⏱ {deadline_clean}</td>
                    </tr>
                    <tr>
                      <td style="padding:10px 14px;font-size:11px;color:#4A5A78;
                                  text-transform:uppercase;letter-spacing:.7px;">Reported By</td>
                      <td style="padding:10px 14px;font-size:13px;
                                  color:#E2E8F6;">{created_by}</td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- ACTION BUTTONS -->
              <tr>
                <td style="padding:20px 32px 0;">
                  <div style="background:#1C1A00;border:1px solid #3D3400;
                               border-radius:10px;padding:14px;text-align:center;">
                    <div style="font-size:12px;color:#FDE68A;margin-bottom:12px;font-weight:600;">
                      ⚡ Act now to avoid SLA breach
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved"
                             style="display:inline-block;background:#10B981;color:#fff;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            ✅ Mark Resolved Now
                          </a>
                        </td>
                        <td align="center" style="padding:0 6px;">
                          <a href="{BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating"
                             style="display:inline-block;background:#F59E0B;color:#000;
                                    font-size:13px;font-weight:700;padding:11px 24px;
                                    border-radius:8px;text-decoration:none;">
                            🔍 Still Investigating
                          </a>
                        </td>
                      </tr>
                    </table>
                  </div>
                </td>
              </tr>

              <!-- FOOTER -->
              <tr>
                <td style="padding:24px 32px;border-top:1px solid #1E2D45;">
                  <p style="font-size:11px;color:#4A5A78;text-align:center;
                              margin:0;line-height:1.7;">
                    This is an automated SLA warning from ResolveNow AI.<br>
                    Ticket <span style="color:#3B82F6;font-family:monospace;">{ticket_id}</span>
                    — Please resolve before the deadline to avoid breach.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    plain = f"""
⚠️ SLA WARNING — ResolveNow AI

Ticket ID   : {ticket_id}
Topic       : {topic}
Priority    : {priority.upper()}
SLA Type    : {sla_type} SLA
% Used      : {percent_used}%
Deadline    : {deadline_clean}
Reported By : {created_by}

You have {remaining_pct}% of the allowed time remaining.
Act now to avoid a breach.

✅ Mark Resolved  : {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=resolved
🔍 Investigating  : {BASE_URL}/tickets/{ticket_id}/agent-resolve?status=investigating
    """.strip()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚠️ [SLA WARNING] {ticket_id} — {sla_type} SLA at {percent_used}% | Act Now"
        msg["From"]    = f"ResolveNow AI <{SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg["X-Priority"] = "2"

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        print(f"  ✅ SLA warning email sent to {to_email} for {ticket_id} ({sla_type})")
        return {"success": True, "message": f"Warning email sent to {to_email}"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Gmail authentication failed"}
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}