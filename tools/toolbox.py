import requests
from datetime import datetime


# ── Tool functions ───────────────────────────────────────────────

def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. No API key needed."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1}
        r = requests.get(url, params=params, timeout=8)
        data = r.json()
        if data.get("AbstractText"):
            return data["AbstractText"][:800]
        topics = data.get("RelatedTopics", [])[:4]
        results = [t["Text"] for t in topics if isinstance(t, dict) and "Text" in t]
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search error: {e}"


def read_file(filepath: str) -> str:
    """Read a text file and return its contents."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:3000]
    except FileNotFoundError:
        return f"Error: file '{filepath}' not found"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(filepath: str, content: str) -> str:
    """Write content to a file (creates the file if it does not exist)."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


def get_datetime(**kwargs) -> str:
    """Return the current date and time."""
    return datetime.now().strftime("%A, %d %B %Y at %H:%M")


# ── Tool registry ────────────────────────────────────────────────
# Each entry: "tool_name": (function, schema_dict)

TOOL_REGISTRY = {
    "web_search": (
        web_search,
        {
            "name": "web_search",
            "description": "Search the web for current information on any topic.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    ),
    "read_file": (
        read_file,
        {
            "name": "read_file",
            "description": "Read the contents of a text file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file"}
                },
                "required": ["filepath"]
            }
        }
    ),
    "write_file": (
        write_file,
        {
            "name": "write_file",
            "description": "Write text content to a file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["filepath", "content"]
            }
        }
    ),
    "get_datetime": (
        get_datetime,
        {
            "name": "get_datetime",
            "description": "Get the current date and time.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ),
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Run a tool by name and return its output as a string."""
    if tool_name not in TOOL_REGISTRY:
        return f"Error: unknown tool '{tool_name}'"
    fn, _ = TOOL_REGISTRY[tool_name]
    try:
        return fn(**tool_input)
    except Exception as e:
        return f"Error running {tool_name}: {e}"
