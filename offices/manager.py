"""
offices/manager.py

The Manager validates agent output against IB rubrics (homework)
or code-quality / accessibility checks (website_code), using
claude-sonnet-4-20250514.
"""

from __future__ import annotations
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic

_SONNET = "claude-sonnet-4-20250514"

RUBRICS_DIR = os.path.join(
    os.path.dirname(__file__), "office1_homework", "rubrics"
)

_SUBJECT_TO_RUBRIC: dict[str, str] = {
    "math_aa_hl":       "math_aa_hl.txt",
    "physics_hl":       "physics_hl.txt",
    "computer_science": "computer_science_hl.txt",
    "english_lang_lit": "english_lang_lit_sl.txt",
    "french_b":         "french_b_sl.txt",
    "economics_sl":     "econ_sl.txt",
    "tok":              "tok.txt",
}


def _load_rubric(subject: str) -> str:
    filename = _SUBJECT_TO_RUBRIC.get(subject)
    if not filename:
        return f"[No rubric mapped for subject '{subject}']"
    path = os.path.join(RUBRICS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"[Rubric file '{filename}' not found]"


class Manager:
    """
    Validates agent output using claude-sonnet-4-20250514.

    validate(output, task_type, context) → dict

      task_type = 'homework'
        Returns: {valid, feedback, score_estimate, re_do_task?}

      task_type = 'website_code'
        Returns: {valid, issues, approved, re_do_task?}

    If valid is False, the returned dict always contains re_do_task — a
    one-paragraph instruction string telling the original agent exactly
    what to fix before resubmitting.
    """

    def __init__(self):
        self.model  = _SONNET
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

    # ------------------------------------------------------------------ #

    def validate(
        self,
        output: str,
        task_type: str,
        context: dict | None = None,
    ) -> dict:
        """
        Validate *output* produced by a subject or website agent.

        Parameters
        ----------
        output    : the text/code the subject agent returned
        task_type : 'homework' or 'website_code'
        context   : extra metadata; for homework pass {'subject': '<key>'}
        """
        context = context or {}

        if task_type == "homework":
            return self._validate_homework(output, context)
        elif task_type == "website_code":
            return self._validate_website_code(output, context)
        else:
            return {
                "valid":    False,
                "feedback": (
                    f"Unknown task_type '{task_type}'. "
                    "Use 'homework' or 'website_code'."
                ),
            }

    # ------------------------------------------------------------------ #
    # Homework validation
    # ------------------------------------------------------------------ #

    def _validate_homework(self, output: str, context: dict) -> dict:
        subject = context.get("subject", "")
        rubric  = _load_rubric(subject)

        system_prompt = (
            "You are an experienced IB examiner and senior tutor. "
            "You receive a student's homework answer and the official IB marking rubric. "
            "Evaluate whether the answer meets IB standards.\n\n"
            "Reply with a single JSON object — no markdown fences, no prose outside JSON. "
            "Required keys:\n"
            '  "valid"          : true if the answer meets the rubric, false otherwise\n'
            '  "feedback"       : concise examiner-style feedback (2–5 sentences)\n'
            '  "score_estimate" : e.g. "6/7" or "Band 3" using the rubric\'s scale\n'
            '  "re_do_task"     : ONLY include if valid is false — a one-paragraph '
            "instruction telling the original agent exactly what to improve and resubmit."
        )

        user_msg = (
            f"SUBJECT: {subject}\n\n"
            f"IB RUBRIC:\n{rubric}\n\n"
            f"STUDENT OUTPUT TO VALIDATE:\n{output}"
        )

        result = self._call_and_parse(system_prompt, user_msg)

        result.setdefault("valid", False)
        result.setdefault("feedback", "")
        result.setdefault("score_estimate", "N/A")

        return result

    # ------------------------------------------------------------------ #
    # Website code validation
    # ------------------------------------------------------------------ #

    def _validate_website_code(self, output: str, context: dict) -> dict:
        system_prompt = (
            "You are a senior software engineer and accessibility auditor. "
            "Review code produced by an AI web-dev agent. "
            "Check for: common bugs, missing error handling, security issues, "
            "and basic WCAG accessibility problems (missing alt text, unlabelled "
            "form controls, keyboard-navigation blockers).\n\n"
            "Reply with a single JSON object — no markdown fences, no prose outside JSON. "
            "Required keys:\n"
            '  "valid"      : true if there are no blocking issues, false otherwise\n'
            '  "issues"     : list of strings describing every problem found '
            "(empty list if none)\n"
            '  "approved"   : true only when valid is true and all issues are minor\n'
            '  "re_do_task" : ONLY include if valid is false — a one-paragraph '
            "instruction telling the original agent exactly what to fix and resubmit."
        )

        user_msg = f"WEBSITE CODE TO REVIEW:\n{output}"

        result = self._call_and_parse(system_prompt, user_msg)

        result.setdefault("valid", False)
        result.setdefault("issues", [])
        result.setdefault("approved", False)

        return result

    # ------------------------------------------------------------------ #
    # Shared LLM call + JSON parse
    # ------------------------------------------------------------------ #

    def _call_and_parse(self, system_prompt: str, user_msg: str) -> dict:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if the model added them anyway
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            return {
                "valid":    False,
                "feedback": f"Manager could not parse its own response as JSON: {e}",
            }
        except Exception as e:
            return {
                "valid":    False,
                "feedback": f"Manager error: {e}",
            }


# ─── Module-level singleton ───────────────────────────────────────────────────

manager = Manager()
