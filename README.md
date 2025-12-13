# 1 MCP Server 🚀

> **MCP of MCPs** — automatically discover and configure MCP servers on your machine (remote or local).

After setup, you can usually just say:

> “I want to perform . Call the `deep_search` tool and follow the outlined steps.”

The goal is that you only install **this** MCP server, and it handles the rest (searching servers, selecting servers, configuring servers, etc.).

### Demo video 🎥: [https://youtu.be/W4EAmaTTb2A](https://youtu.be/W4EAmaTTb2A) 

Choose **one** of the following:

1. **Remote** (fastest)
2. **Local (prebuilt)** — **Docker**, **uvx**, or **npx**
3. **Local (from source)** — run this repo directly

### 1) Remote 🌍

Use the hosted endpoint (recommended for the simplest setup).

**Docs + guided setup:** [https://mcp.1mcpserver.com/](https://mcp.1mcpserver.com/)

#### Configure your MCP client

Add the following entry to your client config file:

* **Cursor**: `./.cursor/mcp.json`
* **Gemini CLI**: `./gemini/settings.json` (see Gemini docs)
* **Claude Desktop**:

  * macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  * Windows: `%APPDATA%\Claude\claude_desktop_config.json`
* **Codex**: see Codex MCP configuration docs

**Remote config (JSON):**

```json
{
  "mcpServers": {
    "1mcpserver": {
      "url": "https://mcp.1mcpserver.com/mcp/",
      "headers": {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache"
      }
    }
  }
}
```

If you already have other servers configured, just merge this entry under `mcpServers`:

```json
{
  "mcpServers": {
    "1mcpserver": {
      "url": "https://mcp.1mcpserver.com/mcp/",
      "headers": {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache"
      }
    },
    "file-system": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

**Tip:** If your client supports it, move the config file into your **home directory** to apply globally.

---

### 2) Local (prebuilt) 💻

Use this when you want everything local, or when your MCP client only supports **STDIO**.

#### 2A) Docker 🐳

> Use this if you want an isolated runtime and a single, reproducible command.

```bash
docker run --rm -i \
  -e DATADIR=/data \
  -v "$PWD/db:/data" \
  <YOUR_DOCKER_IMAGE_HERE>
```

```json
{
  "mcpServers": {
    "1mcpserver": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "DATADIR=/data",
        "-v",
        "${PWD}/db:/data",
        "<YOUR_DOCKER_IMAGE_HERE>"
      ]
    }
  }
}
```

#### 2B) uvx 🐍

> Use this if you publish the server as a Python package and want a one-liner.

```bash
uvx <YOUR_PACKAGE_NAME> --local
```

```json
{
  "mcpServers": {
    "1mcpserver": {
      "command": "uvx",
      "args": ["<YOUR_PACKAGE_NAME>", "--local"]
    }
  }
}
```

#### 2C) npx 📦

> Use this if you publish a Node wrapper / launcher and want a one-liner.

```bash
npx -y <YOUR_NPM_PACKAGE_NAME>
```

```json
{
  "mcpServers": {
    "1mcpserver": {
      "command": "npx",
      "args": ["-y", "<YOUR_NPM_PACKAGE_NAME>"]
    }
  }
}
```

---

### 3) Local (from source) 🧩

Clone this repo and run directly.

```bash
git clone https://github.com/particlefuture/MCPDiscovery.git
cd MCPDiscovery
uv sync
uv run server.py --local
```

```json
{
  "mcpServers": {
    "1mcpserver": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "<PATH_TO_CLONED_REPO>",
        "run",
        "server.py",
        "--local"
      ]
    }
  }
}
```

> If your client supports remote `url` servers, you can use the **Remote** setup instead.

#### Optional: grant file-system access 📁

If you want your LLM to have file-system access, add an MCP filesystem server and point it at the directory you want to allow:

```json
{
  "mcpServers": {
    "file-system": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/"]
    }
  }
}
```

---

## Architecture 🧠

There are two search modes:

### Quick Search ⚡

For explicit requests like: “I want an MCP server that handles payments.”

Returns a shortlist of relevant MCP servers.

### Deep Search 🌊

For higher-level or complex goals like: “Build a website that analyzes other websites.”

The LLM breaks the goal into components/steps, finds MCP servers for each part, and if something is missing, it asks whether to:

* ignore that part,
* break it down further, or
* implement it ourselves.

Deep Search stages:

1. **Planning** — identify servers, keys, and config changes
2. **Testing** — verify servers (via `test_server_template_code`)
3. **Acting** — execute the workflow using the configured servers

---

## Change Log 🕒

* July 31 2025: Upgrade to 0.2.0. Added agentic planning.
* Dec 12 2025: Support for Gemini + Codex
* Dec 13 2025: Easier local setup with docker, npm, and uvx. 

## Future 🔮

* Better demo videos (new domain, narrated walkthrough)
* Model Context Communication Protocol (MCCP): standard server-to-server messaging
* Avoid calling tools with an `internal_` prefix unless instructed
* Improve MCP server database schema: server, description, url, config json, extra setup (docker/api key/etc)

## Credits 🙏

Data sources:

* wong2/awesome-mcp-servers
* metorial/mcp-containers
* punkpeye/awesome-mcp-servers
* modelcontextprotocol/servers

Published to:

* [https://mcpservers.org/](https://mcpservers.org/)
* [https://glama.ai/mcp/servers](https://glama.ai/mcp/servers)

## Troubleshooting 🧰

* If using a venv and you get `ModuleNotFoundError` even after installing: delete the venv and recreate it.
