import os
from dotenv import load_dotenv
from tools.toolbox import calculator, web_search, read_file, write_file, get_datetime
from tools.pronote_tool import get_homework, get_homework_for_subject
from tools.gmail_tool import read_emails, draft_reply
from tools.gdrive_tool import list_files_in_folder, read_text_file

load_dotenv()


# ─── Memory ───────────────────────────────────────────────────────────────────

class Memory:
    """Simple in-process short-term memory (list of dicts)."""

    def __init__(self):
        self.messages: list[dict] = []

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> list[dict]:
        return list(self.messages)

    def clear(self):
        self.messages = []


# ─── Agent ────────────────────────────────────────────────────────────────────

class Agent:
    """
    A simple agent that loops:
      1. Calls the LLM with the current memory.
      2. Checks if the model wants to call a tool.
      3. Runs the tool and adds the result to memory.
      4. Repeats until a final answer is produced.
    """

    def __init__(self, name: str, instructions: str, tools: list):
        self.name = name
        self.instructions = instructions
        self.tools = {t.__name__: t for t in tools}
        self.memory = Memory()

    def reset(self):
        self.memory.clear()


# ─── run_agent ────────────────────────────────────────────────────────────────

def run_agent(task: str, agent: Agent, verbose: bool = True) -> str:
    """
    Drive an agent to completion on *task*.
    Returns the final answer string.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    # Build Gemini tool declarations from the agent's tool callables
    gemini_tools = list(agent.tools.values()) if agent.tools else []

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=agent.instructions,
        tools=gemini_tools if gemini_tools else None,
    )

    chat = model.start_chat(enable_automatic_function_calling=True)

    agent.memory.add("user", task)

    if verbose:
        print(f"\n[{agent.name}] Task: {task}")

    response = chat.send_message(task)
    result = response.text

    agent.memory.add("assistant", result)

    if verbose:
        print(f"[{agent.name}] Result: {result}")

    return result


# ─── AGENTS registry ──────────────────────────────────────────────────────────

general_agent = Agent(
    name="General Assistant",
    instructions=(
        "You are a helpful general-purpose assistant. "
        "Use the available tools whenever needed to answer accurately."
    ),
    tools=[calculator, web_search, read_file, write_file, get_datetime,
           get_homework, get_homework_for_subject,
           read_emails, draft_reply,
           list_files_in_folder, read_text_file],
)

AGENTS: dict[str, Agent] = {
    "general": general_agent,
}
