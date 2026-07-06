import os
import sys
import asyncio

# Ensure parent directory is in PYTHONPATH for easy execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent import get_mcp_toolset, route_query
from app.security import mask_pii, sanitize_input

async def run_cli():
    session_service = InMemorySessionService()
    
    # Create the interaction session
    session = await session_service.create_session(
        app_name="support_copilot",
        user_id="operator_1",
        session_id="session_interactive"
    )
    
    print("\n" + "="*60)
    print("🤖 Customer Support & Technical Escalation Co-pilot CLI")
    print("="*60)
    print("Available Actions:")
    print("  - Submit a query to triage and file a ticket.")
    print("  - Ask a technical/API question for grounded document search.")
    print("  - Escalate a ticket to the engineering backlog (JIRA).")
    print("  - Type 'exit' to quit.")
    print("="*60 + "\n")
    
    while True:
        try:
            query = input("You: ").strip()
            if not query:
                continue
            if query.lower() == 'exit':
                print("Exiting support co-pilot. Goodbye!")
                break
                
            # Input Safety & PII Masking
            try:
                sanitize_input(query)
                clean_query = mask_pii(query)
            except ValueError as security_err:
                print(f"\n🛡️  [Security Blocked] {security_err}\n")
                continue
                
            if clean_query != query:
                print(f"🛡️  [PII Masked] Input sanitized to: \"{clean_query}\"")
                
            selected_agent = route_query(clean_query)

            # Attach MCP toolset only when the selected agent needs it.
            mcp_toolset = None
            if selected_agent.name in ("triage_agent", "escalation_agent"):
                mcp_toolset = get_mcp_toolset()
                selected_agent.tools = [mcp_toolset]

            runner = Runner(
                app_name="support_copilot",
                agent=selected_agent,
                session_service=session_service
            )

            content = types.Content(role='user', parts=[types.Part(text=clean_query)])
            
            print("AI is thinking...")
            events = runner.run_async(
                user_id="operator_1",
                session_id=session.id,
                new_message=content
            )
            
            async for event in events:
                # Print the final generated answer when it's ready
                if event.is_final_response():
                    response_parts = getattr(getattr(event, "content", None), "parts", None) or []
                    response_text = "".join(
                        getattr(part, "text", "") for part in response_parts if getattr(part, "text", None)
                    )
                    if response_text:
                        print(f"\nAgent: {response_text}\n")
                    else:
                        print("\nAgent: No response generated.\n")
                    break

            # Close MCP toolset if we created one for this request.
            if mcp_toolset is not None:
                await mcp_toolset.close()
                    
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError encountered: {e}\n")
            
    # No global MCP toolset to close; instances are closed per-request.

if __name__ == "__main__":
    try:
        asyncio.run(run_cli())
    except Exception as e:
        print(f"CLI session failed: {e}")
