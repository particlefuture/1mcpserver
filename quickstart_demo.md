# QuickStart Demo
Video tutorial: [https://youtu.be/W4EAmaTTb2A](https://youtu.be/W4EAmaTTb2A)
### Here, we show a demo of how to use the MCP server with Cursor or Claude to analyze websites. 

### 0. Setup 1MCPServer
View [README](./README.md) to add our MCP server.

- generate a website for website SEO analysis: Analyze `builtwith.com`
    - Given website, I want it to 
        - tell me the tech stack: builtwith [https://github.com/builtwith/mcp?tab=readme-ov-file](https://github.com/builtwith/mcp?tab=readme-ov-file`0)
        - extract data (this is nondeterministic, depends on the LLM's mood): 
          - builtwith
          - read-website-fast
          - firecrawl [https://github.com/mendableai/firecrawl-mcp-server?tab=readme-ov-file](https://github.com/mendableai/firecrawl-mcp-server?tab=readme-ov-file)
          - webscraping.ai
          - fetch/server-fetch
          - scrapezy

### 1. Prompt to Cursor: 
I want to perform analysis of website. I want to be able to analyze the tech stack the website uses, and extract web data. Call the deep_search tool. 

### 2. Keep pressing allow for the LLM to handle everything
The LLM would think and decide to use a subset of the following (since the LLM is indeterministic, each time you run it you might get a different set of MCP servers): 
- builtwith
- firecrawl
- webscraping.ai
- fetch/server-fetch
- scrapezy

### 3. If you ever need to setup your API key. The LLM would prompt you to do so. Visit the websites and get your API key. 
Now restart you cursor/claude. 


# Detailed YouTube Video Walkthrough: 
Title: Building ANYTHING you want with vibe coding + MCP servers in 5 minutes (pure beginners)

Let's learn to use MCP servers to do anything you want with LLMs in 5 minutes. 
## What is MCP? 
Something we can use that makes the LLMs really powerful. 

## Basic Setup: 
- install cursor: https://cursor.com/downloads
- install uv: https://docs.astral.sh/uv/getting-started/installation/#installation-methods <- using this to run filesystem
## Add MCP server
The next step to do is to spin up cursor to add our first MCP server. In this example, we are going to use 
- 1mcpserver: automatically finds and configures MCP servers for you
- filesystem: gives 1mcpserver the permission to modify mcp config files

  - add a cursor config file `.cursor/mcp.json` with the content:
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
- bring up the command pallet
    - `cmd + shift + p` on macOS
    - `ctrl + shift + p` on Windows/Linux
- type `Open MCP Settings`

Now we can see there are 2 MCPs being added. Toggle them. If you see green, great! If you see anything else, lmk in the comments and I'll try to help. 

## Finding and adding MCP servers
Now in this demo, we are going to show how we can make LLMs an expertise in web analysis. Let's tell cursor to do so. To achieve so, we let the LLMs find and add more MCP servers itself. But this time, the LLM does all the searching and configurations instead of us. 

I want to perform analysis of website. I want to be able to analyze the tech stack the website uses, and extract web data. Call the deep_search tool.

- we see it starts planning
- start finding a bunch of relevant MCP servers. (GPT5 likes to do a lot of searches)
- selects the most relevant and fetches their README for setup instructions
- start configuring the MCP servers
    - let's go grab the API keys
Finally, go ahead and enable them.

## Use them! 
- Use the MCP servers to analyze the website `builtwith.com`
  - Prompt: Use the MCP servers to analyze the website `builtwith.com`. 
  - Get me all the websites listed on the main homepage. 
  - Play around it more. Get data from the website.  

- caveat: When things doesn't work. Normally this is due to the mcp servers' limitations, rather than the workflow or framework.
  - E.g. Amazon.com <- builtwith doesn't work

## Bonus1: Getting around Cursor API Usage Limit
- get your api key
- open cursor -> cursor settings -> API Key -> verify 


## Bonus2: Deep dive into the serer architecture and code