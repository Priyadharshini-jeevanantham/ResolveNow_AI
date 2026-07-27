# backend/agent_roster.py
# Manages agent assignment based on topic and current month

import json
import os
from datetime import datetime
from pathlib import Path

ROSTER_PATH = Path("data/agents/agent_roster.json")


def load_roster() -> dict:
    """Load agent roster from JSON file."""
    if not ROSTER_PATH.exists():
        print(f"WARNING: Roster file not found at {ROSTER_PATH}")
        return {}
    with open(ROSTER_PATH, "r") as f:
        return json.load(f)


def get_current_month_key() -> str:
    """Returns current month key like '2025-05'."""
    return datetime.now().strftime("%Y-%m")


def get_group_for_topic(topic: str, roster: dict) -> str:
    """Find which agent group handles this topic."""
    topic_lower = topic.lower()
    for group_name, group_data in roster.get("groups", {}).items():
        for t in group_data.get("topics", []):
            if t.lower() in topic_lower or topic_lower in t.lower():
                return group_name
    return "General Support"


def get_current_agent(group_name: str, roster: dict) -> dict:
    """
    Get the assigned agent for the current month in the given group.
    Returns dict with name, email, phone.
    """
    month_key = get_current_month_key()
    groups    = roster.get("groups", {})

    if group_name not in groups:
        group_name = "General Support"

    monthly = groups[group_name].get("monthly_agents", {})

    # Try current month first
    if month_key in monthly:
        agent = monthly[month_key]
        return {
            "name":       agent["name"],
            "email":      agent["email"],
            "phone":      agent.get("phone", ""),
            "group":      group_name,
            "month":      month_key,
            "found":      True
        }

    # Fallback — find latest available month
    available = sorted(monthly.keys(), reverse=True)
    if available:
        agent = monthly[available[0]]
        return {
            "name":       agent["name"],
            "email":      agent["email"],
            "phone":      agent.get("phone", ""),
            "group":      group_name,
            "month":      available[0],
            "found":      True,
            "fallback":   True
        }

    return {
        "name":  "Support Team",
        "email": "",
        "phone": "",
        "group": group_name,
        "month": month_key,
        "found": False
    }


def assign_agent(topic: str, agent_group: str = "") -> dict:
    """
    Main function — given a topic, find the right group
    and the current month's assigned agent.

    Returns:
        group_name   : correct agent group
        agent_name   : assigned agent's name
        agent_email  : assigned agent's email
        agent_phone  : assigned agent's phone
        month        : which month this assignment is for
    """
    roster     = load_roster()
    group_name = get_group_for_topic(topic, roster)

    # If user manually specified a group and it exists — respect it
    if agent_group and agent_group in roster.get("groups", {}):
        group_name = agent_group

    agent = get_current_agent(group_name, roster)

    print(f"AGENT ASSIGNED — Group: {group_name} | "
          f"Agent: {agent['name']} | Month: {agent['month']}")

    return {
        "group_name":  group_name,
        "agent_name":  agent["name"],
        "agent_email": agent["email"],
        "agent_phone": agent.get("phone", ""),
        "month":       agent["month"]
    }


def get_all_current_agents() -> list:
    """Get all currently assigned agents across all groups."""
    roster    = load_roster()
    month_key = get_current_month_key()
    result    = []

    for group_name, group_data in roster.get("groups", {}).items():
        monthly = group_data.get("monthly_agents", {})
        agent   = monthly.get(month_key, {})
        if agent:
            result.append({
                "group":       group_name,
                "description": group_data.get("description", ""),
                "topics":      group_data.get("topics", []),
                "agent_name":  agent["name"],
                "agent_email": agent["email"],
                "agent_phone": agent.get("phone", ""),
                "month":       month_key
            })

    return result


def update_agent(group_name: str, month_key: str,
                 name: str, email: str, phone: str = "") -> dict:
    """
    Update a specific agent in the roster.
    Called from the admin API endpoint.
    """
    roster = load_roster()

    if group_name not in roster.get("groups", {}):
        return {"success": False, "message": f"Group '{group_name}' not found"}

    roster["groups"][group_name]["monthly_agents"][month_key] = {
        "name":  name,
        "email": email,
        "phone": phone
    }
    roster["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    with open(ROSTER_PATH, "w") as f:
        json.dump(roster, f, indent=2)

    return {
        "success": True,
        "message": f"Agent updated for {group_name} — {month_key}",
        "agent":   {"name": name, "email": email, "phone": phone}
    }