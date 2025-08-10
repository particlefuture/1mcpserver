import asyncio
import json
import os
import re
from typing import List, Literal, Any
from typing import Tuple, Optional

import requests
from fastapi import HTTPException
from fastmcp import FastMCP
from github import Github
# LangChain RAG imports
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from scrape import INDEX_DIR, DB_PATH, HEADER

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

# perform a similarity search to ensure we can query the vector store
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
API_KEY_PATTERN_RE = re.compile(
    r"\b(?:api[-_ ]?key|apikey|x[-_]api[-_]key)\b",
    re.IGNORECASE
)

def vector_store_search(query: str, top_k: int = 20) -> List[Document]:
    """
    Perform a similarity search over the vector store.
    Returns the top_k entries most similar to `query`.
    """
    try:
        matches = vector_store.similarity_search(query, k=top_k)
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
    return f"""Execute the following steps to fulfill a complex, high-level goal. IF AN API KEY IS REQUIRED, YOU MUST INSTRUCT THE USER TO GET THE API KEY:

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


@mcp.tool(name="find_mcp_config_path_path",
        description=(
            "Determine what the MCP config path is based on users application and operating system. Before calling this tool, you must call `configure_mcp_plan`. "
        ))
def find_mcp_config_path(application: Literal['Cursor', 'Claude'], os: Literal["Mac", "Windows"]= "Mac") -> str:
    config_path = ""
    if application == 'Cursor':
        config_path = "./.cursor/mcp.json"
    elif application == 'Claude':
        if os == "Mac":
            config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        elif os == "Windows":
            config_path = "%APPDATA%\Claude\claude_desktop_config.json"
        else:
            config_path = "Sorry, Linux is not supported. Ask Linus Torvalds to add support for it."
    else:
        config_path = "Couldn't find the MCP config path for the given application. Please specify either 'Cursor' or 'Claude' or add a few lines of code in our github repo."
    return config_path


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
                 top_k: int = 100) -> list[str]:
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

def _parse_github_url(url: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
    """
    Parse a GitHub URL to extract owner, repo, branch (if present), and subpath.
    Examples it understands:
     - https://github.com/owner/repo
     - https://github.com/owner/repo/
     - https://github.com/owner/repo/tree/main/path/to/dir
     - https://github.com/owner/repo/blob/main/path/to/README.md
    Returns (owner, repo, branch, subpath) where branch/subpath may be None.
    """
    if "github.com/" not in url:
        return None
    # Remove protocol
    path = url.split("github.com/", 1)[1]
    path = path.strip().rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")

    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    branch = None
    subpath = None
    if len(parts) >= 3:
        kind = parts[2]  # e.g., "tree" or "blob" or something else
        if kind in ("tree", "blob") and len(parts) >= 4:
            branch = parts[3]
            if len(parts) >= 5:
                subpath = "/".join(parts[4:])
        else:
            # Could be direct owner/repo/<something>; treat that as subpath on default branch
            subpath = "/".join(parts[2:])
    return owner, repo, branch, subpath

@mcp.tool(name="fetch_readme")
def fetch_readme(github_url: str) -> str:
    """
    Fetch the README content for a GitHub URL. If the URL is not for GitHub, returns empty content.
    Attempts to locate the README.md in the indicated directory (e.g., for
    https://github.com/owner/repo/tree/main/path, it fetches README.md inside path).
    First tries raw.githubusercontent.com; if that fails, falls back to PyGithub API.

    Returns JSON string with keys:
      - status: "success" or "error: <message>"
      - require_api_key: bool (heuristic scan)
      - content: README text (empty on error)
      - REMINDER: only present when require_api_key is True
    """
    import os
    import json
    import requests

    try:
        parsed = _parse_github_url(github_url)
        if parsed is None:
            # Not parseable as GitHub URL: return empty content per spec
            result = {
                "status": "error: no support for non github urls for now. ",
                "require_api_key": False,
                "content": ""
            }
            return json.dumps(result)

        owner, repo_name, branch, subpath = parsed

        # Attempt fetching raw README via raw.githubusercontent.com
        # Determine branch: if not in URL, we may need to query API for default branch
        use_branch = branch
        if subpath:
            # Directory: look for README.md inside that dir
            # Avoid naive strip; ensure path ends without trailing slash
            normalized_subpath = subpath.rstrip("/").lstrip("/")
            readme_path_fragment = f"{normalized_subpath}/README.md"
        else:
            # Root: README.md at root
            readme_path_fragment = "README.md"

        raw_content = None

        # If branch unknown, try common defaults first before hitting API
        candidate_branches = []
        if use_branch:
            candidate_branches.append(use_branch)
        else:
            candidate_branches.extend(["main", "master"])

        # We'll only query PyGithub for default branch if raw attempts fail and PyGithub is available
        for br in candidate_branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{br}/{readme_path_fragment}"
            try:
                resp = requests.get(raw_url, headers=HEADER, timeout=10)
                if resp.status_code == 200:
                    raw_content = resp.text
                    use_branch = br
                    break
            except Exception:
                # swallow and continue
                pass

        # If still no content, try to get default branch via API and fetch raw README there
        if raw_content is None:
            print(f"Fetching README from GitHub API for {owner}/{repo_name} on branch {use_branch}")
            try:
                from github import Github
                token = os.getenv("GITHUB_TOKEN", None)
                gh = Github(token) if token else Github()
                repo = gh.get_repo(f"{owner}/{repo_name}")
                if not use_branch:
                    use_branch = getattr(repo, "default_branch", None)
                if use_branch:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{use_branch}/{readme_path_fragment}"
                    resp = requests.get(raw_url, headers=HEADER, timeout=10)
                    if resp.status_code == 200:
                        raw_content = resp.text
                # Fallback: use GitHub API to get the README for that directory
                if raw_content is None:
                    target_dir = subpath or ""
                    candidate_readme_path = (
                        target_dir if target_dir.lower().endswith("readme.md") else f"{target_dir}/README.md"
                    ).lstrip("/")
                    try:
                        content_file = repo.get_contents(candidate_readme_path, ref=use_branch)
                        if content_file and getattr(content_file, "decoded_content", None):
                            raw_content = content_file.decoded_content.decode()
                    except Exception:
                        # Last resort: root README
                        try:
                            root_readme = repo.get_readme(ref=use_branch)
                            raw_content = root_readme.decoded_content.decode()
                        except Exception:
                            pass
            except ImportError:
                # PyGithub not installed; already tried raw.githubusercontent.com
                pass
            except Exception:
                # swallow to allow downstream error handling
                pass

        if raw_content is None:
            result = {
                "status": f"error: could not locate README in '{github_url}' (tried raw fetch and API)",
                "require_api_key": False,
                "content": ""
            }
            return json.dumps(result)

        # Scan for API-key patterns
        require_api_key = bool(API_KEY_PATTERN_RE.search(raw_content))

        result = {
            "status": "success",
            "require_api_key": require_api_key,
            "content": raw_content
        }

        if require_api_key:
            result["REMINDER"] = "IMMEDIATELY INSTRUCT THE USER TO GET THE API KEY"

    except Exception as e:
        result = {
            "status": f"error: {e}",
            "require_api_key": False,
            "content": ""
        }

    return json.dumps(result)



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
