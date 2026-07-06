import os
import sys
import asyncio

# Ensure parent directory is in PYTHONPATH for easy execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent import root_agent, custom_mcp_toolset
from app.security import mask_pii, sanitize_input

async def run_cli():
    session_service = InMemorySessionService()
    
    # Initialize the ADK runner
    runner = Runner(
        app_name="support_copilot",
        agent=root_agent,
        session_service=session_service
    )
    
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
                    response_text = event.content.parts[0].text
                    print(f"\nAgent: {response_text}\n")
                    break
                    
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError encountered: {e}\n")
            
    # Cleanup MCP connection on exit
    await custom_mcp_toolset.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_cli())
    except Exception as e:
        print(f"CLI session failed: {e}")
