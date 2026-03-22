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
    """
    Run a single agent on a task.
    Automatically injects relevant memory context and saves the result.
    """
    from memory.db import build_memory_context, save_memory

    # Build memory context from previous sessions
    memory_ctx = build_memory_context(agent.name, task)
    full_task  = (memory_ctx + task) if memory_ctx else task

    agent.memory.add({"role": "user", "content": full_task})

    if verbose:
        print(f"\nAgent : {agent.name}")
        print(f"Task  : {task}")
        if memory_ctx:
            print(f"Memory: {len(memory_ctx)} chars of context injected")

    result = "No response."

    for iteration in range(10):
        response = client.messages.create(
            model=agent.model,
            max_tokens=2048,
            system=agent.system_prompt,
            tools=agent.tools_schema,
            messages=agent.memory.short_term,
        )

        if response.stop_reason == "end_turn":
            result = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "No response."
            )
            if verbose:
                print(f"Answer: {result}")
            break

        if response.stop_reason == "tool_use":
            agent.memory.add({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if verbose:
                    print(f"  Tool  : {block.name}({json.dumps(block.input)})")
                tool_result = execute_tool(block.name, block.input)
                if verbose:
                    print(f"  Result: {str(tool_result)[:200]}")
                results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     tool_result,
                })
            agent.memory.add({"role": "user", "content": results})

    # Save to persistent memory after every successful run
    try:
        summary = result[:200] if result else ""
        save_memory(
            agent_name=agent.name,
            task=task,
            result=result,
            summary=summary,
        )
    except Exception:
        pass  # Never crash the agent because memory failed

    return result

# ── Define your agents ────────────────────────────────────────────────────
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
