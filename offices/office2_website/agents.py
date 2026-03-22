"""
offices/office2_website/agents.py

6 website-dev team agents + WEBSITE_AGENTS registry dict (Part 8).
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from main import Agent, run_agent
from tools.toolbox import web_search, read_file, write_file, get_datetime
from tools.gdrive_tool import list_files_in_folder, read_text_file


# ── Individual dev agents ──────────────────────────────────────────────────────

product_manager_agent = Agent(
    name="Product Manager",
    instructions=(
        "You are the Product Manager of a web development team. "
        "You define features, write user stories, create project plans, "
        "and coordinate the other team members."
    ),
    tools=[web_search, read_file, write_file, get_datetime,
           list_files_in_folder, read_text_file],
)

frontend_agent = Agent(
    name="Frontend Developer",
    instructions=(
        "You are an expert frontend developer specialising in HTML, CSS, "
        "and vanilla JavaScript. You write clean, accessible, and responsive "
        "UI code."
    ),
    tools=[web_search, read_file, write_file, get_datetime],
)

backend_agent = Agent(
    name="Backend Developer",
    instructions=(
        "You are an expert backend developer specialising in Python and FastAPI. "
        "You design APIs, write server-side logic, and manage databases."
    ),
    tools=[web_search, read_file, write_file, get_datetime],
)

devops_agent = Agent(
    name="DevOps Engineer",
    instructions=(
        "You are a DevOps engineer. You write deployment configs, CI/CD pipelines, "
        "Dockerfiles, and Procfiles. You ensure the app runs smoothly in production."
    ),
    tools=[web_search, read_file, write_file, get_datetime],
)

qa_agent = Agent(
    name="QA Engineer",
    instructions=(
        "You are a QA engineer. You review code for bugs, write test cases, "
        "and ensure the product meets quality standards before release."
    ),
    tools=[web_search, read_file, write_file, get_datetime],
)

tech_writer_agent = Agent(
    name="Technical Writer",
    instructions=(
        "You are a technical writer. You write clear documentation, README files, "
        "API references, and changelogs for the development team."
    ),
    tools=[web_search, read_file, write_file, get_datetime,
           list_files_in_folder, read_text_file],
)


# ── Registry ───────────────────────────────────────────────────────────────────

WEBSITE_AGENTS: dict[str, Agent] = {
    "product_manager": product_manager_agent,
    "frontend":        frontend_agent,
    "backend":         backend_agent,
    "devops":          devops_agent,
    "qa":              qa_agent,
    "tech_writer":     tech_writer_agent,
}
