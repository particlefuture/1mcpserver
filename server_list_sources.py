
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


def get_source4():
    # TODO: Add the anthropic official list
    ...
def get_all_sources():
    s1 = get_source1()
    s2 = get_source2()
    s3 = get_source3()
    return s1 + s2 + s3

