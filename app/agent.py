"""
Multi-agent configuration for the Customer Support & Technical Escalation Co-pilot.

Architecture:
- root_agent (Support Coordinator): Routes incoming requests to specialist sub-agents.
  ├── triage_agent: Classifies tickets and persists them via the custom MCP ticketing server.
  ├── retriever_agent: Answers technical questions using Google Search grounding.
  └── escalation_agent: Manages JIRA escalations with human-in-the-loop approval.

Key ADK concepts demonstrated:
  1. Multi-agent system with delegation (sub_agents)
  2. Custom stdio MCP server (McpToolset + StdioConnectionParams)
  3. Google Search grounding tool (google_search)
  4. before_tool_callback for human-in-the-loop security guardrail
"""

import os
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from app.config import DEFAULT_MODEL, REQUIRE_HUMAN_APPROVAL

# ---------------------------------------------------------------------------
# Custom Ticketing MCP Toolset (stdio subprocess)
# Exposes: list_tickets, add_ticket, escalate_ticket, create_jira_issue
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
mcp_server_script = os.path.join(current_dir, "mcp_server.py")

custom_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            args=[mcp_server_script]
        )
    )
)

# ---------------------------------------------------------------------------
# Security Callbacks
# ---------------------------------------------------------------------------

def human_in_the_loop_callback(tool, args, tool_context):
    """
    before_tool_callback that intercepts create_jira_issue calls and requires
    explicit human approval before allowing the tool to execute.

    This implements the Human-in-the-Loop security pattern from Day 4 of the
    course, ensuring that privileged write operations to the engineering backlog
    always involve a human decision checkpoint.
    """
    if tool.name == "create_jira_issue" and REQUIRE_HUMAN_APPROVAL:
        print("\n" + "=" * 50)
        print("🚨  SECURITY GUARDRAIL: HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
        print("Agent is attempting to create a JIRA issue in the engineering backlog:")
        print(f"  - Associated Ticket ID: {args.get('ticket_id')}")
        print(f"  - Summary: {args.get('summary')}")
        print(f"  - Description: {args.get('description')}")
        print("=" * 50)

        user_input = input("Approve JIRA creation? (y/N): ").strip().lower()
        if user_input != "y":
            print("❌ Escalation rejected by human operator.")
            return {
                "status": "error",
                "error_message": "Escalation rejected by human operator. JIRA issue was not created.",
            }
        print("✅ Escalation approved. Executing tool...")
    return None

# ---------------------------------------------------------------------------
# Sub-Agent: Triage Agent
# Uses the custom MCP ticketing server to create, list, and manage tickets.
# ---------------------------------------------------------------------------
triage_agent = Agent(
    model=DEFAULT_MODEL,
    name="triage_agent",
    description=(
        "Analyzes incoming customer support tickets, classifies them "
        "(Bug, Question, Feature Request), determines severity, and creates "
        "a ticket record in the support database."
    ),
    instruction=(
        "You are the Triage Agent. Analyze incoming support requests and:\n"
        "1. Classify the issue into: Bug, Question, or Feature Request.\n"
        "2. Determine severity: low, medium, or high.\n"
        "3. Call the 'add_ticket' tool to persist the ticket.\n"
        "4. Reply with the full ticket details including the assigned ID.\n"
        "Always be concise and professional."
    ),
    tools=[custom_mcp_toolset],
)

# ---------------------------------------------------------------------------
# Sub-Agent: Knowledge Retriever Agent
# Uses Google Search grounding to answer technical questions with up-to-date,
# authoritative information from official developer documentation.
# ---------------------------------------------------------------------------
retriever_agent = Agent(
    model=DEFAULT_MODEL,
    name="retriever_agent",
    description=(
        "Searches Google and official developer documentation to answer "
        "technical questions about APIs, Cloud Run, ADK, FastMCP, and "
        "deployment best practices."
    ),
    instruction=(
        "You are the Knowledge Retriever Agent. Your role is to answer technical "
        "questions by searching for authoritative information.\n\n"
        "When a user asks a technical or API question:\n"
        "1. Use the 'google_search' tool to search for accurate, up-to-date answers.\n"
        "2. Prioritize results from official sources: adk.dev, cloud.google.com, "
        "   developers.google.com, and official GitHub repositories.\n"
        "3. Synthesize a clear, helpful response grounded in the retrieved content.\n"
        "4. Always cite the source URL(s) you used.\n\n"
        "Focus areas: Google ADK, FastMCP/MCP protocol, Cloud Run deployment, "
        "Python agent patterns, Gemini API, and developer best practices."
    ),
    tools=[google_search],
)

# ---------------------------------------------------------------------------
# Sub-Agent: Escalation Agent
# Manages ticket escalation and JIRA issue creation with HITL protection.
# ---------------------------------------------------------------------------
escalation_agent = Agent(
    model=DEFAULT_MODEL,
    name="escalation_agent",
    description=(
        "Manages ticket escalations and creates JIRA issues for the "
        "engineering backlog for confirmed bug reports."
    ),
    instruction=(
        "You are the Escalation Agent. Your tasks:\n"
        "1. When asked to escalate a ticket, call 'escalate_ticket' with the ticket ID.\n"
        "2. When asked to create a JIRA issue, call 'create_jira_issue' with the "
        "   ticket_id, a concise summary, and a detailed description.\n"
        "3. NOTE: Creating JIRA issues requires human approval — you will be prompted "
        "   automatically. Inform the user if the escalation was approved or rejected.\n"
        "4. You can also call 'list_tickets' to find ticket details if the user "
        "   references a ticket by description rather than ID."
    ),
    tools=[custom_mcp_toolset],
    before_tool_callback=human_in_the_loop_callback,
)

# ---------------------------------------------------------------------------
# Root Orchestrator Agent: Support Coordinator
# Routes all incoming user requests to the appropriate specialist sub-agent.
# ---------------------------------------------------------------------------
root_agent = Agent(
    model=DEFAULT_MODEL,
    name="support_coordinator",
    description="The main support team coordinator. Triages new requests and delegates tasks to specialist agents.",
    instruction=(
        "You are the Support Coordinator Agent. You lead a team of support specialists:\n"
        "  - 'triage_agent': Classifies and files new support tickets.\n"
        "  - 'retriever_agent': Answers technical and API questions using real-time search.\n"
        "  - 'escalation_agent': Escalates tickets and creates JIRA engineering issues.\n\n"
        "Routing rules:\n"
        "1. New customer issue or complaint → delegate to 'triage_agent'.\n"
        "2. Technical question (how-to, API, deployment, debugging) → delegate to 'retriever_agent'.\n"
        "3. Request to escalate a ticket or create a JIRA issue → delegate to 'escalation_agent'.\n\n"
        "Always delegate to the appropriate sub-agent. Do not answer technical questions directly."
    ),
    sub_agents=[triage_agent, retriever_agent, escalation_agent],
)
