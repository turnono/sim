from google.genai import types


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def display_state(
    session_service, app_name, user_id, session_id, label="Current State"
):
    """Display the current session state in a formatted way."""
    try:
        session = session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )

        # Format the output with clear sections
        print(f"\n{'-' * 10} {label} {'-' * 10}")

        # Handle the user name (with our "user:" prefix)
        user_name = session.state.get("user:name", "Unknown")
        print(f"👤 User: {user_name}")
        
        # Show timezone info
        timezone = session.state.get("user:timezone", "Unknown")
        print(f"🌍 Timezone: {timezone}")

        # Handle reminders (with our "user:" prefix and structured format)
        reminders = session.state.get("user:reminders", [])
        if reminders:
            print("📝 Reminders:")
            for idx, reminder in enumerate(reminders, 1):
                # Handle both string reminders and structured reminders
                if isinstance(reminder, dict):
                    reminder_text = reminder.get("text", "No text")
                    completed = "✅" if reminder.get("completed", False) else "❌"
                    print(f"  {idx}. {reminder_text} {completed}")
                else:
                    print(f"  {idx}. {reminder}")
        else:
            print("📝 Reminders: None")

        # Show conversation metrics
        turn_count = session.state.get("conversation_turn_count", 0)
        print(f"💬 Conversation Turns: {turn_count}")
        
        # Print other user preferences
        print("⚙️ Other Preferences:")
        for k, v in session.state.items():
            if k.startswith("user:") and k not in ["user:name", "user:timezone", "user:reminders"]:
                key = k.replace("user:", "")
                print(f"  {key}: {v}")

        print("-" * (22 + len(label)))
    except Exception as e:
        print(f"Error displaying state: {e}")


async def process_agent_response(event):
    """Process the response event from the agent."""
    if event.content and event.content.parts:
        text = event.content.parts[0].text
        if text:
            print(f"\n{Colors.BLUE}{Colors.BOLD}{event.author}:{Colors.RESET} {text}")
            return text
    return None


async def call_agent_async(runner, user_id, session_id, query):
    """Call the agent asynchronously with the user's query."""
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(
        f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}"
    )
    final_response_text = None

    # Display state before processing
    display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State BEFORE processing",
    )

    try:
        # Using run_async method with async iterator pattern
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            # Process each event and get the final response if available
            response = await process_agent_response(event)
            if response:
                final_response_text = response
    except Exception as e:
        print(f"Error during agent call: {e}")

    # Display state after processing the message
    display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State AFTER processing",
    )

    return final_response_text 