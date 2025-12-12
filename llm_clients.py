from enum import Enum
from typing import Final


class Application(str, Enum):
    CURSOR = "Cursor"
    CLAUDE = "Claude"
    GEMINICLI = "Gemini"
    CODEX = "Codex"


class OS(str, Enum):
    MAC = "Mac"
    WINDOWS = "Windows"
    LINUX = "Linux"
    
    
# app → os → path
MCP_CONFIG_PATHS: Final[dict[Application, dict[OS, str]]] = {
    Application.CURSOR: {
        OS.MAC: "./.cursor/mcp.json",
        OS.WINDOWS: r'.\.cursor\mcp.json',
    },
    Application.CLAUDE: {
        OS.MAC: "~/Library/Application Support/Claude/claude_desktop_config.json",
        OS.WINDOWS: r"%APPDATA%\Claude\claude_desktop_config.json",
    },
    Application.GEMINICLI: {
        OS.MAC: "./gemini/settings.json",
        OS.WINDOWS: r'.\gemini\settings.json',
    },
    Application.CODEX: {
        OS.MAC: "~/.codex/config.toml"
    }
}

