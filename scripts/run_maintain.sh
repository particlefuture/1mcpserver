#!/usr/bin/env bash
set -euo pipefail

# 1. Go to your project directory
cd /Users/jiazhenghao/CodingProjects/MCP/mcp-on-cloudrun

# 3. Run your scraper
pip3 install uv
uv run maintain.py

# 4. Commit & push
git switch release
git pull
git add .
git commit -m "update DB $(date +'%Y-%m-%d')"
git push