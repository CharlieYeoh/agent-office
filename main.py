import os
import json
import anthropic
from dotenv import load_dotenv
from tools.toolbox import TOOL_REGISTRY, execute_tool

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ── Memory ────────────────────────────────────────────────────────────────
class Memory:
    def __init__(self):
        self.short_term = []
        self.long_term  = []

    def add(self, message: dict):
        self.short_term.append(message)
        if len(self.short_term) > 20:
            dropped = self.short_term.pop(0)
            if dropped.get("role") == "assistant":
                self.long_term.append(str(dropped.get("content", ""))[:120])


# ── Agent ─────────────────────────────────────────────────────────────────
class Agent:
    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        tool_names: list,
        model: str = "claude-haiku-4-5-20251001",
        system_prompt_override: str = None,
    ):
        self.name                   = name
        self.role                   = role
        self.goal                   = goal
        self.tool_names             = tool_names
        self.model                  = model
        self.memory                 = Memory()
        self._system_prompt_override = system_prompt_override

    @property
    def system_prompt(self) -> str:
        if self._system_prompt_override:
            return self._system_prompt_override
        return (
            f"You are {self.role}.\n"
            f"Your goal: {self.goal}\n\n"
            "Be concise. Use tools when they help."
        )

    @property
    def tools_schema(self) -> list:
        return [
            TOOL_REGISTRY[n][1]
            for n in self.tool_names
            if n in TOOL_REGISTRY
        ]


# ── Agent loop ────────────────────────────────────────────────────────────
def run_agent(task: str, agent: Agent, verbose: bool = True) -> str:
    agent.memory.add({"role": "user", "content": task})
    if verbose:
        print(f"\nAgent : {agent.name}")
        print(f"Task  : {task}")

    for iteration in range(10):
        response = client.messages.create(
            model=agent.model,
            max_tokens=2048,
            system=agent.system_prompt,
            tools=agent.tools_schema,
            messages=agent.memory.short_term,
        )

        if response.stop_reason == "end_turn":
            answer = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "No response."
            )
            if verbose:
                print(f"Answer: {answer}")
            return answer

        if response.stop_reason == "tool_use":
            agent.memory.add({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if verbose:
                    print(f"  Tool  : {block.name}({json.dumps(block.input)})")
                result = execute_tool(block.name, block.input)
                if verbose:
                    print(f"  Result: {str(result)[:200]}")
                results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     result,
                })
            agent.memory.add({"role": "user", "content": results})

    return "Agent did not finish within 10 steps."


# ── Basic agents (original three) ─────────────────────────────────────────
AGENTS = {
    "researcher": Agent(
        name="Researcher",
        role="a thorough research agent",
        goal="find accurate answers using web search",
        tool_names=["web_search", "get_datetime"],
    ),
    "writer": Agent(
        name="Writer",
        role="a clear writing agent",
        goal="produce well-written text and summaries",
        tool_names=["read_file", "write_file", "get_datetime"],
    ),
    "scheduler": Agent(
        name="Scheduler",
        role="a personal assistant and scheduler",
        goal="help organise tasks, plans, and daily schedules",
        tool_names=["get_datetime", "read_file", "write_file"],
    ),
}


if __name__ == "__main__":
    result = run_agent(
        "What day of the week is it today?",
        AGENTS["scheduler"]
    )