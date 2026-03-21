import os
import sys

# Make sure Python can find main.py (it lives one level up from api/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from main import AGENTS, run_agent

app = FastAPI()

# Allow the browser to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    agent: str   # must match a key in AGENTS
    task: str    # what the user wants done


@app.get("/agents")
def list_agents():
    """Return the list of available agent names."""
    return {"agents": list(AGENTS.keys())}


@app.post("/run")
def run_task(req: TaskRequest):
    """Run an agent task and return the result."""
    if req.agent not in AGENTS:
        return {"error": f"Unknown agent: {req.agent}"}
    agent = AGENTS[req.agent]
    # Reset memory so each web request is fresh
    from main import Memory
    agent.memory = Memory()
    result = run_agent(req.task, agent, verbose=False)
    return {"result": result}


# Serve the frontend HTML file at the root URL
@app.get("/")
def serve_frontend():
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "index.html"
    )
    return FileResponse(frontend_path)


