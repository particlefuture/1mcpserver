# 1 MCP Server: A MCP server that picks and configures MCP servers for you
> MCP of MCPs. Automatic discovery and configure MCP servers on your local machine. Remote! 

We aim at providing only this MCP server. Then you can leave all the rest (searching servers, selecting servers, configuring servers, etc) all to this MCP server.

No need to run setup commands, no need to acquire api keys. Just need to modify one file.



### Demo video: https://youtu.be/Kv2HgD9hRZ8 
# Set up Instruction

### Simple remote setup: integration with Cursor and Claude (Option 1) 
Add the following to curson or claude MCP config file. 

**For Cursor**: Open `~/.cursor/mcp.json`

**For Claude**: Open 
- macOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`


**Add the following to the file:** 
```json
{
  "mcpServers": {
    "mcp-server-discovery": {
      "url": "https://mcp.1mcpserver.com/mcp/",
      "headers": {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "API_KEY": "value"
      }
    }
  }
}
```
If you are already using other servers, the json file should look like this
```json
{
    "mcpServers": {
        "mcp-server-discovery": {
            "url": "https://mcp.1mcpserver.com/mcp/",
            "headers": {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
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

### (Option 2) Local Setup with STDIO
```
git clone https://github.com/particlefuture/MCPDiscovery.git
cd MCPDiscovery
uv sync
uv run server.py
```
Unfortunately, up to the time this md file is updated, claude only allows stdio. So you'd have to modify `server.py` to use STDIO. Find the main block in `server.py`, comment out the "Streamable HTTP server BLOCK" and uncomment the "Standard I/O server BLOCK". Final code should look like this
```python
    asyncio.run(
        mcp.run_async(
            transport="stdio",
        )
    )
```

The mcp.json should look like this: 
```json
{
    "mcpServers": {
        "mcp-servers-discovery": {
            "command": "/Users/jiazhenghao/.local/bin/uv",
            "args": [
                "--directory",
                "{PATH_TO_THE_CLONED_REPO}",
                "run",
                "server.py", 
               "--local"
            ]
        },
        "file-system": {
            "command": "node",
            "args": [
                "{FILE_SYSTEM_CLONED_PATH}/filesystem/index.ts",
                "~/"
            ]
        }
    }
}
```

## Architecture
There are two types of search tools: quick search and a deep search. 
### Quick Search
When the user has an explicit goal of what type of MCP they want ("I want a MCP server that handles payment"), this tool just gives back a list of mcp servers.
### Deep Search <sup>*</sup>
When the user has a high level or complex description of the goal ("Build me a website that analyzes other websites"). The LLM need to break it down into multiple steps and components (I need to analyze the website traffic, I need to analyze the website tech stack, I need to show some web data, ...), then find MCP servers for each step. If a corresponding MCP server doesn't exist, inform the user to see if we should ignore this component, break it down further, or implement it ourselves. 

I refer to this as horizontal expansion and vertical expansion. Horizontal expansion is for finding independent components, vertical expansion is for finding steps that have to be done sequentially (more like fetch, analyze, generate graph). In the above example, those are all horizontal expansions.  


There are multiple stages in the deep search:
1. Planning stage: 
    - setup mcp servers: 
        - get and configure API keys as needed, provide users with instructions of obtaining API keys 
        - modify the mcp.json files. 
2. Testing stage:
    - test to see if they servers are working. Call `test_server_template_code` tool, which return a simple client testing code example.  
3. Acting stage: 
    - build the workflow/application by calling the MCP servers

*We're supposed to put deep search as a prompt, but both cursor and claude rarely calls prompts. 


# Change Log:
- July 31 2025: Upgrade to 0.2.0. Added agentic planning. For complex tasks, the server now prompts the LLM to perform multi-step MCP server query.
- 
### Future
- improve the demo videos: new domain name, actual example, voice explanation
- Call For MCCP (Model Context Communication Protocol): Standard way of communicating between MCP servers. Motivation: Allow directly sending requests to other mcp servers (each mcp server might also have dependencies). (But would also need stricter supervision)
- shouldn't call functions with a leading prefix `internal_` unless instructed by MCP servers 

- Better database for MCP servers. It should be in structure: server, description, url, config json, (optionally, additional setup, docker, api_key, etc)


### This repo is based on these repos. Huge thanks to the author and contributors of these repos.
Data source: 
- wong2/awesome-mcp-servers
- metorial/mcp-containers
- punkpeye/awesome-mcp-servers
- modelcontextprotocol/servers

Published to: 
- https://mcpservers.org/
- https://glama.ai/mcp/servers
- 

### More about the repo
Motivation and Context: 
> Right now, most MCP server search are done via github searching or online google search. There has been several MCP wrappers, but most serves as an middleware infrastructure that hosts different MCP at an endpoint. The gathering of which MCP to host is still mostly done by manual search. We provide an automatic pipeline of not only searching but also automatically configuring MCP servers.

How Has This Been Tested?
> Tested with Claude and Cursor with both remote endpoint and local stdio. Tested the demo for 10 times. 




# Trouble shooting
- If using venv, ModuleNotFoundError even after installing the module -> delete venv and create a new venv. 

