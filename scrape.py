import requests
import re
import os
import sqlite3
from typing import List

from dotenv import load_dotenv

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

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

# Scraping functions

def clean_text(text: str) -> List[str]:
    """
    Remove tags, bold markdown, new lines, and common emoji ranges from the given text.
    """
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("**", "").replace("__", "").replace("\n", "")
    clean = re.sub(r"[^\x00-\x7F]+", "", clean)
    return clean


def get_source1():
    repo_url = (
        "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/refs/heads/main/README.md"
    )
    response = requests.get(repo_url, headers=HEADER)
    section = response.text.split("## Server Implementations", 1)[1]
    section = section.split("## Frameworks", 1)[0]
    lines = [clean_text(ln) for ln in section.splitlines() if ln.startswith("- ")]
    return lines


def get_source2():
    repo_url = "https://raw.githubusercontent.com/metorial/mcp-containers/refs/heads/main/README.md"
    response = requests.get(repo_url, headers=HEADER)
    text = response.text
    text = re.sub(r'<img[^>]*>', '', text)
    text = re.sub(r'\*\*', '', text)
    section = text.split("## Featured Servers", 1)[1]
    section = section.split("# License", 1)[0].replace("## Available Servers", '')
    lines = [clean_text(ln) for ln in section.split("\n\n") if ln.strip().startswith("- ")]
    return lines


def get_source3():
    repo_url = "https://raw.githubusercontent.com/wong2/awesome-mcp-servers/refs/heads/main/README.md"
    response = requests.get(repo_url, headers=HEADER)
    section = response.text.split("## Official Servers", 1)[1]
    section = section.split("## Clients", 1)[0].replace("## Community Servers", '')
    lines = [clean_text(ln) for ln in section.splitlines() if ln.strip().startswith("- ")]
    return lines


def get_all_sources():
    s1 = get_source1()
    s2 = get_source2()
    s3 = get_source3()
    return s1 + s2 + s3

# Database functions

def create_db_and_table(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            name TEXT PRIMARY KEY,
            description TEXT,
            url TEXT
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
                continue
            name, url, description = match.groups()
            servers.append((name, description, url))
    return servers


def update_db(db_path, servers):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for name, description, url in servers:
        c.execute('SELECT 1 FROM servers WHERE url = ?', (url,))
        if c.fetchone() is None:
            try:
                response = requests.get(url, headers=HEADER, timeout=10)
                if response.status_code == 200:
                    try:
                        c.execute('''
                            INSERT INTO servers (name, description, url)
                            VALUES (?, ?, ?)
                        ''', (name, description, url))
                        print(f"Added: {name}, {url} to {DB_PATH}")
                    except sqlite3.IntegrityError:
                        print(f"Name conflict: {name}, {url}")
                elif response.status_code == 404:
                    # Remove without logging
                    c.execute('DELETE FROM servers WHERE url = ?', (url,))
                elif response.status_code == 403:
                    print(f"Access denied for {url}: HTTP 403 Forbidden, Skipping as well. ")
                else:
                    print(f"Skipping {url}: HTTP {response.status_code}")
            except Exception as e:
                print(f"Error accessing {url}: {e}")
    conn.commit()
    conn.close()


def generate_embeddings(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name, description, url FROM servers')
    rows = c.fetchall()
    conn.close()

    docs = [Document(page_content=desc, metadata={"name": name, "url": url}) for name, desc, url in rows]
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(INDEX_DIR)
    return vector_store

# Main workflow
if __name__ == '__main__':
    # 1. Scrape and write to text file
    sources = get_all_sources()
    with open(TXT_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(sources))
    print(f"Scraped {len(sources)} server entries to {TXT_PATH}")

    # 2. Initialize DB
    create_db_and_table(DB_PATH)

    # 3. Clean up unreachable entries for prev database --> Moved to maintain.py

    # 4. Read scraped entries and update DB
    servers = read_servers_from_txt(TXT_PATH)
    if servers:
        update_db(DB_PATH, servers)
    else:
        print(f"No valid servers found in {TXT_PATH}")

    # 5. Generate and save embeddings
    generate_embeddings(DB_PATH)
    print("Finished scraping, DB update, and embedding generation.")