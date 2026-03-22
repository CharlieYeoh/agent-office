import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from main import AGENTS, run_agent, client
from offices.office1_homework.agents import HOMEWORK_AGENTS
from offices.office2_website.agents import WEBSITE_AGENTS
from offices.manager import Manager

mgr = Manager(client)


def run_with_validation(task, agent, task_type, subject=None, max_retries=2):
    from main import Memory
    for attempt in range(max_retries + 1):
        agent.memory = Memory()
        result = run_agent(task, agent, verbose=False)
        validation = mgr.validate(result, task_type, subject)
        if validation['valid']:
            return {'result': result, 'validation': validation, 'attempts': attempt + 1}
        if attempt < max_retries:
            task = task + '\n\nManager feedback: ' + validation['feedback']
    return {'result': result, 'validation': validation, 'attempts': max_retries + 1}


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    agent: str
    task: str


class HomeworkRequest(BaseModel):
    subject: str
    task: str


class WebsiteRequest(BaseModel):
    agent: str
    task: str


class ValidateRequest(BaseModel):
    output: str
    task_type: str
    subject: str | None = None
    context: dict | None = None


@app.get("/agents")
def list_agents():
    """Return the list of available agent names."""
    return {"agents": list(AGENTS.keys())}


@app.post("/run")
def run_task(req: TaskRequest):
    """Run a basic agent task and return the result."""
    if req.agent not in AGENTS:
        return {"error": f"Unknown agent: {req.agent}"}
    agent = AGENTS[req.agent]
    from main import Memory
    agent.memory = Memory()
    result = run_agent(req.task, agent, verbose=False)
    return {"result": result}


@app.post("/homework")
def run_homework(req: HomeworkRequest):
    """Run a specific homework subject agent with manager validation."""
    if req.subject not in HOMEWORK_AGENTS:
        return {"error": f"Unknown subject '{req.subject}'. Valid subjects: "
                         "math_aa_hl, physics_hl, computer_science, "
                         "english_lang_lit, french_b, economics_sl, tok"}
    agent = HOMEWORK_AGENTS[req.subject]
    return run_with_validation(req.task, agent, "homework", subject=req.subject)


@app.get("/homework/fetch")
def fetch_all_homework():
    """
    Run all 7 subject agents in parallel using a thread pool.
    All agents start simultaneously — roughly 7x faster than sequential.
    """
    subjects = [
        "math_aa_hl", "physics_hl", "computer_science",
        "english_lang_lit", "french_b", "economics_sl", "tok"
    ]

    task = (
        "Fetch my homework for your subject from Pronote. "
        "For each task: if you can complete it, do so with full working shown. "
        "If it requires a file submission or cannot be done without materials, "
        "mark it as 'Needs input' and explain what is needed."
    )

    def run_subject(name):
        try:
            agent = HOMEWORK_AGENTS[name]
            from main import Memory
            agent.memory = Memory()
            result = run_agent(task, agent, verbose=False)
            return name, result
        except Exception as e:
            return name, f"Error: {e}"

    results = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(run_subject, name): name for name in subjects}
        for future in futures:
            name, result = future.result()
            results[name] = result

    return results


@app.get("/emails")
def fetch_emails():
    """Run the email agent to read inbox and draft suggested replies."""
    agent = HOMEWORK_AGENTS["email"]
    from main import Memory
    agent.memory = Memory()
    result = run_agent(
        "Read my latest 10 emails labelled 'school'. For each one that needs a reply, "
        "draft an appropriate response and save it as a Gmail draft. "
        "Return a summary of what you found and what drafts you created.",
        agent, verbose=False
    )
    return {"result": result}


@app.post("/website")
def run_website_agent(req: WebsiteRequest):
    """Run a specific website dev team agent with manager validation."""
    if req.agent not in WEBSITE_AGENTS:
        return {"error": f"Unknown agent: {req.agent}. Valid agents: "
                         "product_manager, ui_designer, frontend_dev, "
                         "backend_dev, qa_tester, devops"}
    agent = WEBSITE_AGENTS[req.agent]
    return run_with_validation(req.task, agent, "website_code")


@app.post("/validate")
def validate_output(req: ValidateRequest):
    """Run the Manager to validate agent output against IB rubrics or code quality."""
    ctx = req.context or {}
    if req.subject:
        ctx["subject"] = req.subject
    result = mgr.validate(
        output=req.output,
        task_type=req.task_type,
        subject=req.subject,
        context=str(ctx),
    )
    return result


@app.get("/office1")
def serve_office1():
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "office1.html"
    )
    return FileResponse(frontend_path)


@app.get("/office2")
def serve_office2():
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "office2.html"
    )
    return FileResponse(frontend_path)


@app.get("/")
def serve_frontend():
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "index.html"
    )
    return FileResponse(frontend_path)