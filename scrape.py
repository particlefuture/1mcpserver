import time

import requests
import re
import os
import sqlite3
import json
from typing import List, Tuple

from dotenv import load_dotenv

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from github import RateLimitExceededException

from server_list_sources import get_all_sources
# ---------------------------------------------------------------------
# If fetch_readme is in the same file, this import isn't needed.
# If it's in another module, replace the direct call below accordingly.
# from my_readme_fetcher import fetch_readme
# ---------------------------------------------------------------------

load_dotenv()
GH_TOKEN = os.getenv("GITHUB_TOKEN")

# Constants
HEADER = {
    "Authorization": f"Bearer {GH_TOKEN}",  # use “token” scheme for PAT
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    )
}
DB_PATH = 'db/server_list.db'
TXT_PATH = 'db/mcp_servers.txt'
INDEX_DIR = "db/faiss_index"

# ---------------------------
# Scraping helper(s)
# ---------------------------

def clean_text(text: str) -> List[str]:
    """
    Remove tags, bold markdown, new lines, and common emoji ranges from the given text.
    """
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("**", "").replace("__", "").replace("\n", "")
    clean = re.sub(r"[^\x00-\x7F]+", "", clean)
    return clean





# ---------------------------
# DB: schema & migration
# ---------------------------

def create_db_and_table(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            name TEXT,
            description TEXT,
            url TEXT PRIMARY KEY,
            readme_content TEXT,
            fetch_error TEXT,
            require_api_key INTEGER DEFAULT 0, 
            config_setup_cmd TEXT,
            additional_cmd TEXT 
        )
    ''')
    conn.commit()

    conn.close()


def read_servers_from_txt(txt_path):
    servers = []
    if not os.path.exists(txt_path):
        return servers
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r'- \[([^\]]+)\]\(([^)]+)\)\s*-\s*(.+)', line)
            if not match:
                print(f"Skipping unrecognized line format: {line}")
                continue
            name, url, description = match.groups()
            servers.append((name, description, url))
    return servers

# ---------------------------
# README integration
# ---------------------------

from helpers.github_urls import _parse_github_url, API_KEY_PATTERN_RE
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
            result[
                "REMINDER"] = "IMMEDIATELY INSTRUCT THE USER TO GET THE API KEY. PROVIDE THEM WITH THE URL IF POSSIBLE."

    except Exception as e:
        result = {
            "status": f"error: {e}",
            "require_api_key": False,
            "content": ""
        }

    return json.dumps(result)

def _extract_readme_fields(github_url: str):
    """
    Calls your fetch_readme(github_url) and returns a tuple:
      (readme_content, fetch_error, require_api_key_int)
    """
    try:
        result_raw = fetch_readme(github_url)
        data = json.loads(result_raw) if isinstance(result_raw, str) else result_raw

        status = data.get("status", "")
        content = data.get("content", "") or ""
        require_api_key = 1 if data.get("require_api_key", False) else 0

        # If status starts with "error:", stash the message in fetch_error, else ""
        fetch_error = status if (isinstance(status, str) and status.lower().startswith("error")) else ""

        return content, fetch_error, require_api_key
    except RateLimitExceededException as e:
        # wait and retry in 1 hour
        print("GitHub API rate limit exceeded. Sleeping for 1 hour before retrying...")
        time.sleep(3600)  # sleep for 1 hour
        return _extract_readme_fields(github_url)

    except Exception as e:
        # Defensive: treat as fetch error but keep the row
        return "", f"error: {e}", 0

# ---------------------------
# Updater
# ---------------------------

def update_db(db_path, servers):
    """
    servers: iterable of (name, description, url)
    - Validates URL reachability
    - Fetches README + API-key flag using fetch_readme
    - Upserts by URL (URL is the conflict target). Existing rows are overwritten.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for name, description, url in servers:
        try:
            response = requests.get(url, headers=HEADER, timeout=10)
            if response.status_code == 200:
                readme_content, fetch_error, require_api_key = _extract_readme_fields(url)

                # Overwrite the entire row when the same URL already exists.
                c.execute('''
                    INSERT INTO servers (name, description, url, readme_content, fetch_error, require_api_key)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        name = excluded.name,
                        description = excluded.description,
                        readme_content = excluded.readme_content,
                        fetch_error = excluded.fetch_error,
                        require_api_key = excluded.require_api_key
                ''', (name, description, url, readme_content, fetch_error, require_api_key))

                print(f"Upserted by URL: {url} (name={name}) "
                      f"(api_key={require_api_key}, err={fetch_error if fetch_error else 'no'})")

            elif response.status_code == 404:
                # Remove unreachable entries (by URL)
                c.execute('DELETE FROM servers WHERE url = ?', (url,))
            elif response.status_code == 403:
                print(f"Access denied for {url}: HTTP 403 Forbidden, skipping.")
            else:
                print(f"Skipping {url}: HTTP {response.status_code}")

        except Exception as e:
            # Record error but still upsert so we keep a row keyed by URL
            readme_content, fetch_error, require_api_key = "", f"error: {e}", 0
            c.execute('''
                INSERT INTO servers (name, description, url, readme_content, fetch_error, require_api_key)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO DO NOTHING
                    name = excluded.name,
                    description = excluded.description,
                    readme_content = excluded.readme_content,
                    fetch_error = excluded.fetch_error,
                    require_api_key = excluded.require_api_key
            ''', (name, description, url, readme_content, fetch_error, require_api_key))
            print(f"Error accessing {url}: {e}")

    conn.commit()
    conn.close()

# ---------------------------
# Embeddings (now include README)
# ---------------------------

def generate_embeddings(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # include README content when present
    c.execute('SELECT name, description, url, readme_content FROM servers')
    rows = c.fetchall()
    conn.close()

    docs = []
    for name, desc, url, readme in rows:
        # Combine description + README for richer retrieval
        page_content = ((desc or "") + "\n\n" + (readme or "")).strip()
        if not page_content:
            # Avoid empty docs that can cause embedding errors
            page_content = desc or ""
        docs.append(Document(page_content=page_content, metadata={"name": name, "url": url}))

    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(docs, embeddings)
    os.makedirs(INDEX_DIR, exist_ok=True)
    vector_store.save_local(INDEX_DIR)
    return vector_store

# ---------------------------
# Main workflow
# ---------------------------

if __name__ == '__main__':
    # # 1. Scrape and write to text file
    # sources = get_all_sources()
    # os.makedirs(os.path.dirname(TXT_PATH), exist_ok=True)
    # with open(TXT_PATH, 'w', encoding='utf-8') as f:
    #     f.write("\n".join(sources))
    # print(f"Scraped {len(sources)} server entries to {TXT_PATH}")

    # 2. Initialize / migrate DB
    create_db_and_table(DB_PATH)

    # 3. Read scraped entries and update DB (with README + flags)
    servers = read_servers_from_txt(TXT_PATH)
    if servers:
        update_db(DB_PATH, servers)
    else:
        print(f"No valid servers found in {TXT_PATH}")

    # 4. Generate and save embeddings (now includes README content)
    generate_embeddings(DB_PATH)
    print("Finished scraping, DB update, and embedding generation.")
