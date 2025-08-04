#!/usr/bin/env bash
set -euo pipefail

# 1. Go to your project directory
cd /Users/jiazhenghao/CodingProjects/MCP/MCPDiscovery/

# 3. Run your scraper
source .venv/bin/activate
uv run scrape.py

# 4. Commit & push
git switch release
git pull
git add .
git commit -m "maintain DB $(date +'%Y-%m-%d')"
git push