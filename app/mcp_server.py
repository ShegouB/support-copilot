import os
import json
import logging
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tickets.json")

# Initialize FastMCP Server
mcp = FastMCP("Support Ticketing Database")

def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        default_data = {
            "tickets": [
                {
                    "id": 1,
                    "title": "Database connection timeout",
                    "description": "The database times out when calling run_async under heavy load.",
                    "category": "Bug",
                    "severity": "high",
                    "status": "open"
                },
                {
                    "id": 2,
                    "title": "How to retrieve user context in tool?",
                    "description": "Cannot find documentation for ToolContext in Python ADK.",
                    "category": "Question",
                    "severity": "low",
                    "status": "resolved"
                }
            ],
            "jira_issues": []
        }
        save_db(default_data)
        return default_data
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading database: {e}")
        return {"tickets": [], "jira_issues": []}

def save_db(data: Dict[str, Any]):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving database: {e}")

@mcp.tool()
def list_tickets() -> str:
    """List all customer support tickets in the database.
    
    Returns:
        A JSON string containing the list of all tickets.
    """
    logger.info("MCP Tool: list_tickets called")
    db = load_db()
    return json.dumps(db["tickets"], indent=2)

@mcp.tool()
def add_ticket(title: str, description: str, category: str, severity: str) -> str:
    """Create a new customer support ticket in the database.
    
    Args:
        title: The summary of the issue.
        description: Detailed explanation of the issue.
        category: The category (e.g., 'Bug', 'Question', 'Feature Request').
        severity: The severity level ('low', 'medium', 'high').
        
    Returns:
        A JSON string of the newly created ticket.
    """
    logger.info(f"MCP Tool: add_ticket called - {title} ({category})")
    db = load_db()
    
    new_id = max([t["id"] for t in db["tickets"]], default=0) + 1
    new_ticket = {
        "id": new_id,
        "title": title,
        "description": description,
        "category": category,
        "severity": severity,
        "status": "open"
    }
    db["tickets"].append(new_ticket)
    save_db(db)
    return json.dumps(new_ticket, indent=2)

@mcp.tool()
def escalate_ticket(ticket_id: int) -> str:
    """Escalate an existing customer support ticket to 'high' severity and change status to 'escalated'.
    
    Args:
        ticket_id: The unique ID of the ticket.
        
    Returns:
        A message confirming escalation or indicating ticket not found.
    """
    logger.info(f"MCP Tool: escalate_ticket called for ID: {ticket_id}")
    db = load_db()
    for t in db["tickets"]:
        if t["id"] == ticket_id:
            t["severity"] = "high"
            t["status"] = "escalated"
            save_db(db)
            return f"Ticket {ticket_id} escalated successfully."
    return f"Ticket with ID {ticket_id} not found."

@mcp.tool()
def create_jira_issue(ticket_id: int, summary: str, description: str) -> str:
    """Create a JIRA issue in the simulated engineering backlog for a bug ticket.
    
    Args:
        ticket_id: The ID of the support ticket associated with this bug.
        summary: Short summary of the bug.
        description: Detailed steps to reproduce or bug description.
        
    Returns:
        A JSON string containing the JIRA issue details including the issue key.
    """
    logger.info(f"MCP Tool: create_jira_issue called for Ticket ID: {ticket_id}")
    db = load_db()
    
    jira_key = f"ENG-{100 + len(db['jira_issues']) + 1}"
    jira_issue = {
        "key": jira_key,
        "ticket_id": ticket_id,
        "summary": summary,
        "description": description,
        "status": "BACKLOG"
    }
    db["jira_issues"].append(jira_issue)
    
    # Update the associated ticket status to 'jira_created'
    for t in db["tickets"]:
        if t["id"] == ticket_id:
            t["status"] = "jira_created"
            break
            
    save_db(db)
    return json.dumps(jira_issue, indent=2)

if __name__ == "__main__":
    # Start the FastMCP stdio server
    mcp.run()
