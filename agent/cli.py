import asyncio
import sys

async def run_cli(triage_agent, tools=None):
    """
    Runs the interactive CLI loop for the Triage Agent.
    """
    print("\n[+] Triage Agent is ready. Type your queries below (Ctrl+C to exit).")
    if not tools:
        print("[!] WARNING: No tools were loaded. The agent will be unable to query logs or metrics.")
    
    messages = []
    
    while True:
        try:
            # Use run_in_executor for synchronous input() in an async loop
            user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: input("\n>>> "))
            if not user_input.strip():
                continue
            
            messages.append(("user", user_input))
            
            try:
                print("\n[Thinking...]")
                response = await triage_agent.ainvoke({
                    "messages": messages
                })
                
                # Update conversation history
                messages = response["messages"]
                
                # Find and display the new messages from this specific turn
                new_messages = []
                for msg in reversed(messages):
                    if msg.type == "user":
                        break
                    new_messages.insert(0, msg)
                
                found_ai_content = False
                for msg in new_messages:
                    # 1. Show tool calls
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"    -> Calling Tool: {tc['name']}")
                            print(f"       Args: {tc['args']}")
                    
                    # 2. Show tool results
                    if msg.type == "tool":
                        content_str = str(msg.content)
                        print(f"    -> Tool Result: {content_str[:150]}...")
                    
                    # 3. Show final AI response
                    if msg.type == "ai" and msg.content and msg.content.strip():
                        print(f"\n[Agent]:\n{msg.content.strip()}")
                        found_ai_content = True
                
                if not found_ai_content and not any(getattr(m, 'tool_calls', None) for m in new_messages):
                     print("\n[Agent]: (The agent responded but provided no content or tool calls. This may be a model limitation.)")
                
            except Exception as e:
                print(f"\n[!] The agent encountered an internal error during execution:")
                print(f"  {type(e).__name__}: {str(e)}")
                print(f"\n[!] Please try rephrasing your prompt or give the agent a hint.")
                
                # Inform the LLM that its tool call failed so it can retry
                error_msg = f"The previous action failed with a fatal error: {type(e).__name__}: {str(e)}\nPlease try a different approach or fix your tool query."
                messages.append(("system", error_msg))
                
        except (KeyboardInterrupt, EOFError):
            print("\n\n[+] Exiting CLI. Goodbye!")
            break
