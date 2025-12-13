import requests
import re
from config import HEADER
from typing import List

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
    repo_url = "https://raw.githubusercontent.com/wong2/awesome-mcp-servers/refs/heads/main/README.md"
    response = requests.get(repo_url, headers=HEADER)
    section = response.text.split("## Official Servers", 1)[1]
    section = section.split("## Clients", 1)[0].replace("## Community Servers", '')
    lines = [clean_text(ln) for ln in section.splitlines() if ln.strip().startswith("- ")]
    return lines


def get_source3():
    """
    Get only the officer servers and community server
    """
    repo_url = "https://raw.githubusercontent.com/modelcontextprotocol/servers/refs/heads/main/README.md"
    text = requests.get(repo_url, headers=HEADER).text
    
    OFF_HDR = "### 🎖️ Official Integrations"
    END_HDR = "## 📚 Frameworks"  # the section after Community Servers.
    
    section = text.split(OFF_HDR, 1)[1].split(END_HDR, 1)[0]
    
    bullet_re = re.compile(r"^-\s+.*?\[([^\]]+)\]\(([^)]+)\).*?\s-\s(.+)$")
    
    out: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        m = bullet_re.match(line)
        if not m:
            continue
        name, url, desc = (s.strip() for s in m.groups())
        out.append(f"- [{name}]({url}) - {desc}")
    
    return out

def get_all_sources():
    s1 = get_source1()
    s2 = get_source2()
    s3 = get_source3()
    return s1 + s2 + s3

if __name__ == '__main__':
    servers = get_all_sources()
    for server in servers:
        print(f"{server}")