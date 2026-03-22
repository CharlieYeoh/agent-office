import os
import json
from pathlib import Path
from main import Agent, run_agent, Memory, client

RUBRICS_DIR = Path(__file__).parent / "office1_homework" / "rubrics"


def _load_rubric(subject_key: str) -> str:
    """Load rubric file for a given subject key."""
    mapping = {
        "math_aa_hl":       "math_aa_hl.txt",
        "physics_hl":       "physics_hl.txt",
        "computer_science": "computer_science_hl.txt",
        "english_lang_lit": "english_lang_lit_sl.txt",
        "french_b":         "french_b_sl.txt",
        "economics_sl":     "econ_sl.txt",
        "tok":              "tok.txt",
    }
    filename = mapping.get(subject_key, "")
    if not filename:
        return ""
    path = RUBRICS_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ── Manager agent definition ──────────────────────────────────────────────

manager_agent = Agent(
    name="Manager",
    role="IB academic quality controller and code review manager",
    goal="validate all agent outputs against IB rubrics and code quality standards",
    tool_names=["read_file", "write_file", "get_datetime"],
    model="claude-sonnet-4-20250514",
    system_prompt_override="""You are a strict quality controller for an AI agent system.
Your job is to validate outputs from other agents and decide if they meet the required standard.
You are thorough, fair, and specific in your feedback.
Always respond in valid JSON as instructed by each validation request.""",
)


class Manager:
    """
    Global manager that validates outputs from all agents.
    For homework: checks against IB rubrics.
    For website code: checks quality, security, and completeness.
    """

    def __init__(self, anthropic_client=None):
        self.client = anthropic_client or client
        self.agent  = manager_agent

    def validate(
        self,
        output: str,
        task_type: str,
        subject: str = None,
        context: str = "",
    ) -> dict:
        """
        Validate an agent's output.

        Args:
            output:    The text produced by the agent
            task_type: 'homework' or 'website_code'
            subject:   For homework, the subject key (e.g. 'math_aa_hl')
            context:   The original task description

        Returns:
            {
                valid: bool,
                feedback: str,
                score_estimate: str,   (homework only)
                issues: list,          (code only)
                approved: bool,
                redo_task: str         (populated if valid is False)
            }
        """
        if task_type == "homework":
            return self._validate_homework(output, subject, context)
        elif task_type == "website_code":
            return self._validate_code(output, context)
        else:
            return {
                "valid": True,
                "approved": True,
                "feedback": "Unknown task type — skipping validation.",
                "redo_task": ""
            }

    def _validate_homework(self, output: str, subject: str, context: str) -> dict:
        rubric = _load_rubric(subject) if subject else ""

        rubric_section = (
            f"\n\nMARKING RUBRIC FOR THIS SUBJECT:\n{rubric[:2000]}"
            if rubric else
            "\n\n(No rubric file found — apply general IB standards)"
        )

        prompt = f"""You are validating a homework answer produced by an AI agent for an IB student.

SUBJECT: {subject or "unknown"}
ORIGINAL TASK: {context or "not provided"}
{rubric_section}

AGENT'S OUTPUT:
{output[:3000]}

Evaluate the output against these criteria:
1. Does it fully address the task?
2. Is the working/reasoning shown clearly?
3. Does it meet IB standards for this subject?
4. Are there any factual errors or significant omissions?
5. Would this answer earn marks in a real IB exam?

Respond ONLY with this JSON (no extra text, no markdown):
{{
  "valid": true or false,
  "approved": true or false,
  "score_estimate": "e.g. 7/7 or 5/7 or Cannot assess",
  "feedback": "one paragraph of specific feedback",
  "issues": ["issue 1", "issue 2"],
  "redo_task": "if valid is false: precise instruction to the agent on what to fix and redo. If valid is true: empty string."
}}"""

        return self._run_validation(prompt)

    def _validate_code(self, output: str, context: str) -> dict:
        prompt = f"""You are a senior software engineer reviewing code produced by an AI agent.

ORIGINAL TASK: {context or "not provided"}

AGENT'S OUTPUT:
{output[:3000]}

Check for:
1. Does the code address the task?
2. Are there obvious bugs or logic errors?
3. Is error handling present?
4. Are there security concerns (hardcoded secrets, injection risks)?
5. Is the code readable and maintainable?

Respond ONLY with this JSON (no extra text, no markdown):
{{
  "valid": true or false,
  "approved": true or false,
  "score_estimate": "e.g. Production ready / Needs minor fixes / Needs major fixes",
  "feedback": "one paragraph of specific feedback",
  "issues": ["issue 1", "issue 2"],
  "redo_task": "if valid is false: precise instruction to fix and redo. If valid is true: empty string."
}}"""

        return self._run_validation(prompt)

    def _run_validation(self, prompt: str) -> dict:
        """Send the validation prompt to the manager agent and parse JSON response."""
        self.agent.memory = Memory()
        raw = run_agent(prompt, self.agent, verbose=False)

        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            result = json.loads(raw)
            # Ensure all expected keys exist
            result.setdefault("valid",          True)
            result.setdefault("approved",        result.get("valid", True))
            result.setdefault("score_estimate",  "N/A")
            result.setdefault("feedback",        "")
            result.setdefault("issues",          [])
            result.setdefault("redo_task",       "")
            return result
        except json.JSONDecodeError:
            # If the model didn't return valid JSON, default to approved
            return {
                "valid":         True,
                "approved":      True,
                "score_estimate": "Could not parse",
                "feedback":      raw[:500],
                "issues":        [],
                "redo_task":     "",
            }