"""
offices/office1_homework/agents.py

8 IB homework agents + the HOMEWORK_AGENTS registry dict.
Each subject agent loads its rubric from rubrics/<subject>.txt and knows
the Pronote subject name from .env for fetching homework.
"""

from __future__ import annotations
import os
import sys

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from main import Agent
from tools.toolbox import web_search, write_file, get_datetime
from tools.pronote_tool import get_homework_for_subject
from tools.gmail_tool import read_emails, draft_reply
from tools.gdrive_tool import list_files_in_folder, read_text_file

RUBRICS_DIR = os.path.join(os.path.dirname(__file__), "rubrics")

_HAIKU  = "claude-haiku-4-5-20251001"
_SONNET = "claude-sonnet-4-20250514"


def _load_rubric(filename: str) -> str:
    path = os.path.join(RUBRICS_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            f"[Rubric file '{filename}' not found – "
            "add it to offices/office1_homework/rubrics/]"
        )


# ─── math_aa_hl ───────────────────────────────────────────────────────────────

_MATH_SUBJECT = os.environ.get("PRONOTE_MATH_SUBJECT", "Math Analysis and Approaches HL")

math_aa_hl_agent = Agent(
    name="Math AA HL Agent",
    instructions=(
        "You are an expert IB Mathematics Analysis & Approaches HL tutor.\n"
        f"Your student's Pronote subject name is: '{_MATH_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "Math exercises reference page and exercise numbers from the AA HL textbook. "
        "Show full working for every step — partial credit is given for correct method "
        "even with a wrong final answer.\n\n"
        "RUBRIC:\n"
        + _load_rubric("math_aa_hl.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
math_aa_hl_agent.model = _HAIKU


# ─── physics_hl ───────────────────────────────────────────────────────────────

_PHYSICS_SUBJECT = os.environ.get("PRONOTE_PHYSICS_SUBJECT", "Physics HL")

physics_hl_agent = Agent(
    name="Physics HL Agent",
    instructions=(
        "You are an expert IB Physics HL tutor.\n"
        f"Your student's Pronote subject name is: '{_PHYSICS_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "Physics exercises may be stored in Google Drive. Always check Drive for exercise "
        "files using the folder name 'Physics' before answering. "
        "Always include units and show all substitutions into formulae.\n\n"
        "RUBRIC:\n"
        + _load_rubric("physics_hl.txt")
    ),
    tools=[get_homework_for_subject, list_files_in_folder, read_text_file,
           write_file, web_search, get_datetime],
)
physics_hl_agent.model = _HAIKU


# ─── computer_science ─────────────────────────────────────────────────────────

_CS_SUBJECT = os.environ.get("PRONOTE_CS_SUBJECT", "Computer Science")

computer_science_agent = Agent(
    name="Computer Science Agent",
    instructions=(
        "You are an expert IB Computer Science HL tutor.\n"
        f"Your student's Pronote subject name is: '{_CS_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "For pseudocode questions, use IB pseudocode conventions exactly.\n\n"
        "RUBRIC:\n"
        + _load_rubric("computer_science_hl.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
computer_science_agent.model = _HAIKU


# ─── english_lang_lit ─────────────────────────────────────────────────────────

_ENGLISH_SUBJECT = os.environ.get("PRONOTE_ENGLISH_SUBJECT", "English Language and Literature SL")

english_lang_lit_agent = Agent(
    name="English Language and Literature SL Agent",
    instructions=(
        "You are an expert IB English Language and Literature SL tutor.\n"
        f"Your student's Pronote subject name is: '{_ENGLISH_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "Always integrate quotations. Analyse language features, not just content.\n\n"
        "RUBRIC:\n"
        + _load_rubric("english_lang_lit_sl.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
english_lang_lit_agent.model = _HAIKU


# ─── french_b ─────────────────────────────────────────────────────────────────

_FRENCH_SUBJECT = os.environ.get("PRONOTE_FRENCH_SUBJECT", "French B")

french_b_agent = Agent(
    name="French B SL Agent",
    instructions=(
        "Tu es un tuteur expert en Français B SL du Programme du Diplôme de l'IB.\n"
        f"Le nom de la matière de ton élève sur Pronote est : '{_FRENCH_SUBJECT}'.\n"
        "Lorsque tu récupères les devoirs, utilise ce nom exact avec get_homework_for_subject.\n"
        "Toutes les réponses doivent être en français. "
        "Utilise le registre approprié selon le type de tâche demandée.\n\n"
        "RUBRIQUE:\n"
        + _load_rubric("french_b_sl.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
french_b_agent.model = _HAIKU


# ─── economics_sl ─────────────────────────────────────────────────────────────

_ECON_SUBJECT = os.environ.get("PRONOTE_ECON_SUBJECT", "Economics")

economics_sl_agent = Agent(
    name="Economics SL Agent",
    instructions=(
        "You are an expert IB Economics SL tutor.\n"
        f"Your student's Pronote subject name is: '{_ECON_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "Always include a labelled diagram where relevant. "
        "Evaluate with real-world examples.\n\n"
        "RUBRIC:\n"
        + _load_rubric("econ_sl.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
economics_sl_agent.model = _HAIKU


# ─── tok ──────────────────────────────────────────────────────────────────────

_TOK_SUBJECT = os.environ.get("PRONOTE_TOK_SUBJECT", "Theory of Knowledge")

tok_agent = Agent(
    name="TOK Agent",
    instructions=(
        "You are an expert IB Theory of Knowledge tutor.\n"
        f"Your student's Pronote subject name is: '{_TOK_SUBJECT}'.\n"
        "When fetching homework, use that exact subject name with get_homework_for_subject.\n"
        "Always frame answers around knowledge questions. "
        "Use first and second-order claims.\n\n"
        "RUBRIC:\n"
        + _load_rubric("tok.txt")
    ),
    tools=[get_homework_for_subject, web_search, write_file, get_datetime],
)
tok_agent.model = _HAIKU


# ─── email_agent ──────────────────────────────────────────────────────────────

email_agent = Agent(
    name="Email Agent",
    instructions=(
        "You are a polite student email assistant. "
        "Read incoming emails and draft appropriate replies. "
        "For CAS emails: confirm attendance or ask for details. "
        "For teacher emails: reply formally and concisely. "
        "Never send emails — only save drafts for the student to review."
    ),
    tools=[read_emails, draft_reply, get_datetime],
)
email_agent.model = _HAIKU


# ─── Registry ─────────────────────────────────────────────────────────────────

HOMEWORK_AGENTS: dict[str, Agent] = {
    "math_aa_hl":       math_aa_hl_agent,
    "physics_hl":       physics_hl_agent,
    "computer_science": computer_science_agent,
    "english_lang_lit": english_lang_lit_agent,
    "french_b":         french_b_agent,
    "economics_sl":     economics_sl_agent,
    "tok":              tok_agent,
    "email":            email_agent,
}
