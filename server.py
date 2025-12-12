from pathlib import Path

import asyncio
import json
import os
import re
from typing import List, Literal, Any, Dict
from typing import Tuple, Optional
import os
from pathlib import Path

from fastapi.responses import FileResponse, PlainTextResponse
from starlette.requests import Request
import requests
from fastapi import HTTPException
from fastmcp import FastMCP
from github import Github
# LangChain RAG imports
from langchain_core.documents.base import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from scrape import INDEX_DIR, DB_PATH, HEADER

DOCS_DIR = Path(__file__).parent / "docs"

# If openai api key not present, run load_dotenv
if not os.environ.get("OPENAI_API_KEY"):
    try:
        # try .env file
        from dotenv import load_dotenv

        load_dotenv()
    except Exception as e:
        print(f"Failed to load .env file: {e}, no way to get an OPENAI_API_KEY")

token = os.getenv("GITHUB_TOKEN", None)
gh = Github(token) if token else Github()
# -----------------------------------------------------------------------------
# 1. Global constants and vars
# -----------------------------------------------------------------------------
entries: List[dict] = []
vector_store: FAISS

# -----------------------------------------------------------------------------
# 2. Create/Load Faiss db
# -----------------------------------------------------------------------------
# @on_event("startup")
# Load FAISS index with metadata
embeddings = OpenAIEmbeddings()
if os.path.isdir(INDEX_DIR):
    vector_store = FAISS.load_local(
        INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )

else:  # Vector Database is empty, so we need to build the index
    import sqlite3

    # Load all rows from SQLite once
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, url FROM servers")
    rows = cursor.fetchall()
    conn.close()
    # Build in-memory list and corresponding Documents with metadata
    docs = []
    for name, description, url in rows:
        entries.append({"name": name, "description": description, "url": url})
        docs.append(Document(
            page_content=description,
            metadata={"name": name, "url": url}
        ))
    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(INDEX_DIR)

def test_vector_store():
    """
    Test the vector store by performing a similarity search.
    """
    try:
        res = vector_store.similarity_search("weather", k=1)
        print(f"Result: {res}.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize vector store: {e}")

# -----------------------------------------------------------------------------
# 3. Initialize FastMCP, register tool
# -----------------------------------------------------------------------------
mcp = FastMCP("MCP Server Discovery")

# compiling the api key pattern for fetch_readme.md only once here:


# -----------------------------------------------------------------------------
# LANDING PAGE
# -----------------------------------------------------------------------------

def _file_or_404(p: Path):
    if p.is_file():
        # Add a tiny bit of caching for static assets
        headers = {}
        if any(part == "_next" for part in p.parts):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return FileResponse(p, headers=headers)
    return PlainTextResponse("Not Found", status_code=404)


@mcp.custom_route("/", methods=["GET"])
async def serve_root(_: Request):
    return _file_or_404(DOCS_DIR / "index.html")

@mcp.custom_route("/_next/{rest:path}", methods=["GET"])
async def serve_next(request: Request):
    if request is not None:
        req = request.base_url
        print(f"Got _next request: {req} requesting for url {request.url}")
    rest = request.path_params.get("rest", "")
    print(request.path_params)
    print(f"Serving _next file: {rest}")
    return _file_or_404(DOCS_DIR / f"_next/{rest}")


# Serve any other file that lives under docs/ (images, css, js, favicon, etc.)
# e.g. /assets/logo.png, /robots.txt, /sitemap.xml, /favicon.ico
@mcp.custom_route("/{rest:path}", methods=["GET"])
async def serve_any(request: Request):
    # Try exact file first
    rest = request.path_params.get("rest", "")
    file_resp = _file_or_404(DOCS_DIR / rest)
    if file_resp.status_code == 200:
        return file_resp
    # Optional SPA-style fallback: if you want unknown paths to render index.html
    # (useful if you have client-side routing)
    # return _file_or_404(_safe_path("index.html"))
    return file_resp
# -----------------------------------------------------------------------------
# END OF LANDING PAGE
# -----------------------------------------------------------------------------

def vector_store_search(query: str, top_k: int = 20) -> List[Document]:
    """
    Perform a similarity search over the vector store.
    Returns the top_k entries most similar to `query`.
    """
    try:
        matches = vector_store.similarity_search(query, k=top_k, fetch_k=10000)
        return matches
    except Exception as e:
        return []


@mcp.tool()
def deep_search_planning():
    """
    Given a high-level user goal, if the goal cannot be fulfilled by a single MCP server,
    break it into smaller components/steps, find corresponding MCP servers for each component,
    and then set up the servers. IF AN API KEY IS REQUIRED, YOU MUST INSTRUCT THE USER TO GET THE API KEY.
    """
    return f"""Execute the following steps to fulfill a complex, high-level goal. IF AN API KEY IS REQUIRED, YOU MUST PROVIDE INSTRUCTIONS TO THE USERS TO GET THE API KEY:

1. **Decompose the Goal if Necessary**
   - Call the `quick_search` tool to find MCP servers that match the user’s goal.
   - If the returned server does not completely fulfill the user's goal or requirements, break down the user’s description into smaller discrete components.  

2. **Find MCP Servers**  
   For each component:  
   a. Use the `quick_search` tool to locate the best-matching MCP server.  
   b. If a server’s functionality does not match exactly, inform the user and ask whether to:  
      - Ignore this component  
      - Break it down further  
      - Implement it custom  

3. **Configure Servers**  
   For each MCP server:  
   a. **Fetch Documentation**  
      - Call the `fetch_readme` tool to retrieve its README. REMEMBER to ask the user to configure credentials if the readme requires an API key.  
   b. **Configure Credentials**  
      - Scan the README for API-key or credential requirements.  
      - If there is an API KEY, Immediately provide the user with instructions to obtain any missing keys.  
      - Store configured keys in the environment or secrets file.  
   c. **Prepare MCP Config**  
      1. Invoke `configure_mcp_plan()` to generate the local plan for updating `mcp.json`.  
      2. Use `find_mcp_config_path` to locate the correct `mcp.json` path for this server.  
      3. Use the filesystem mcp server tool to read the current `mcp.json`.  
      4. Use the `add_mcp_tool` to produce the new JSON content.  
      5. Use the filesystem mcp server tool to write the updated content back.  

4. **Finalize**  
   - Once all servers are configured, summarize the completed setup steps and next actions for the user."""


@mcp.tool()
def configure_mcp_plan():
    """
    Returns a plan for the next steps to do.
    """
    return f"""Execute the following steps to add the mcp server:
    1. Ask for the raw json mcp content. 
    2. Use the find_mcp_config_path tool to determine the path to the mcp. (Determine the application and operating system yourself)
    3. Create the mcp config file if not exist.  
    4. Use the filesystem mcp server to read the content.  
    5. Validate the content to write to mcp server by calling `validate_mcp_config` tool. 
    6. Use the filesystem mcp server to write the new content to the mcp config file with the updated content. The new content must be a json object with a top-level `mcpServers` key, whose value is an object mapping server names to their configurations.  
    """


from llm_clients import Application, OS, MCP_CONFIG_PATHS


# @mcp.tool(name="find_mcp_config_path_path", description="Determine what the MCP config path is based on users application and operating system.",)
# def find_mcp_config_path_test(application: Application, os: OS = OS.MAC,) -> str:
#     app_config = MCP_CONFIG_PATHS.get(application)
#     if app_config is None:
#         return "Couldn't find the MCP config path for the given application. Please add it to MCP_CONFIG_PATHS."
#
#     path = app_config.get(os)
#     if path is None:
#         if os is OS.LINUX:
#             return "Sorry, Linux is not supported. Ask Linus Torvalds to add support for it."
#         return f"Couldn't find the MCP config path for {application.value} on {os.value}. Please add it to MCP_CONFIG_PATHS."
#     return path


@mcp.tool(
    name="find_mcp_config_path_path",
    description=(
        "Determine what the MCP config path is based on users application and operating system. You should be able to infor the application. "
        "Before calling this tool, you must call `configure_mcp_plan`."
    ),
)
def find_mcp_config_path(
    application: Application,
    os: OS = OS.MAC,
) -> str:
    app_config = MCP_CONFIG_PATHS.get(application)
    if app_config is None:
        return (
            "Couldn't find the MCP config path for the given application. "
            "Please add it to MCP_CONFIG_PATHS."
        )

    path = app_config.get(os)
    if path is None:
        if os is OS.LINUX:
            return "Sorry, Linux is not supported. Ask Linus Torvalds to add support for it."
        return (
            f"Couldn't find the MCP config path for {application.value} on {os.value}. "
            "Please add it to MCP_CONFIG_PATHS."
        )

    return path


@mcp.tool(name="validate_mcp_config_content")
def validate_mcp_config(mcp_config_content: str) -> bool:
    """
    Validate the MCP config content.
    The content must be a JSON object with a top-level `mcpServers` key,
    whose value is an object mapping server names to their configurations.

    Returns True if the content meets the minimal schema, False otherwise.
    """
    try:
        obj = json.loads(mcp_config_content)
    except json.JSONDecodeError:
        return False

    if not isinstance(obj, dict):
        return False

    # top level key must be `mcpServers`
    mcp_servers = obj.get("mcpServers")
    if not isinstance(mcp_servers, dict):
        return False

    allowed_types = {"local", "http", "sse", "stdio"}

    def is_str_dict(d: Any) -> bool:
        if not isinstance(d, dict):
            return False
        return all(isinstance(k, str) and isinstance(v, str) for k, v in d.items())

    for name, cfg in mcp_servers.items():
        if not isinstance(name, str):
            return False
        if not isinstance(cfg, dict):
            return False

        has_command = "command" in cfg and isinstance(cfg["command"], str)
        has_url = "url" in cfg and isinstance(cfg["url"], str)

        if not (has_command or has_url):
            # minimally one of command or url must exist
            return False

        if "args" in cfg:
            if not isinstance(cfg["args"], list) or not all(isinstance(a, str) for a in cfg["args"]):
                return False

        if "env" in cfg:
            if not is_str_dict(cfg["env"]):
                return False

        if "headers" in cfg:
            if not is_str_dict(cfg["headers"]):
                return False

        if "type" in cfg:
            if not isinstance(cfg["type"], str) or cfg["type"] not in allowed_types:
                return False

        if "tools" in cfg:
            tools = cfg["tools"]
            if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
                return False
            # wildcard allowed
            if len(tools) == 1 and tools[0] == "*":
                pass  # okay
        # other fields are tolerated

    return True


@mcp.tool()
def quick_search(query: str,
                 top_k: int = 50) -> list[dict[str, str]]:
    """
    This tool is for queries with explicit description of MCP functionality.
    Given a free-text MCP description query, return the top_k matching MCP servers text descriptions
    
    Args:
        query (str): A free-text query describing the desired MCP server.
    Returns:
        list[str]: A list of dictionaries, each containing:
    """

    matches = vector_store_search(query, top_k)
    if not matches:
        raise HTTPException(status_code=404, detail="No results found")

    results = []
    for doc in matches:
        md = doc.metadata or {}
        results.append({
            "name": md.get("name", ""),
            "description": doc.page_content,
            "url": md.get("url", "")
        })
    
    return results


@mcp.tool()
def file_system_config_setup():
    """
    This tool is for configuring the MCP server via filesystem.
    It will ask the user to provide the MCP config file path and the content to write.
    """
    return """If the file_system mcp server is not installed yet, update the MCP config file with the following content: 
```json
{
    "mcpServers": {
        "mcp-server-discovery": {
            "url": "https://mcp.1mcpserver.com/mcp/",
            "headers": {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }
        },
        "file-system": {
            "command": "node",
            "args": [
                "/Users/jiazhenghao/CodingProjects/MCP/filesystem/index.ts",
                "~/"
            ]
        }
    }
}
```
"""


@mcp.tool(name="fetch_readme")
def fetch_readme(github_url: str) -> str:
    """
    Fetch the README content for a GitHub URL from the database.
    
    Returns JSON string with keys:
      - status: "success" or "error: <message>"
      - require_api_key: bool (from database)
      - content: README text (empty on error)
      - REMINDER: only present when require_api_key is True
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT readme_content, require_api_key FROM servers WHERE url = ?",
            (github_url,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            print(f"No match found in database for URL: {github_url}")
            result = {
                "status": f"error: no match found in database for URL: {github_url}",
                "require_api_key": False,
                "content": ""
            }
            return json.dumps(result)
        
        readme_content, require_api_key = row
        require_api_key_bool = bool(require_api_key) if require_api_key is not None else False
        
        result = {
            "status": "success",
            "require_api_key": require_api_key_bool,
            "content": readme_content or ""
        }
        
        if require_api_key_bool:
            result["REMINDER"] = "IMMEDIATELY INSTRUCT THE USER TO GET THE API KEY. PROVIDE THEM WITH THE URL IF POSSIBLE."
        
        return json.dumps(result)
        
    except Exception as e:
        print(f"Error fetching readme from database for URL {github_url}: {e}")
        result = {
            "status": f"error: {e}",
            "require_api_key": False,
            "content": ""
        }
        return json.dumps(result)


def test_fetch_readme():
    """
    Test the fetch_readme tool by fetching the README content for a GitHub URL.
    """
    result = fetch_readme("https://github.com/1mcp-app/agent")
    print(result)


# -----------------------------------------------------------------------------
# 4. Run as a stdio MCP server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run MCP Server Discovery")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run server locally via stdio instead of HTTP",
    )
    args = parser.parse_args()

    if args.local:
        # ---- Standard I/O server BLOCK ----
        asyncio.run(
            mcp.run_async(
                transport="stdio",
            )
        )
    else:
        # ---- Streamable HTTP server BLOCK ----
        asyncio.run(
            mcp.run_async(
                transport="streamable-http",
                host="0.0.0.0",
                port=int(os.getenv("PORT", 8080)),
            )
        )


