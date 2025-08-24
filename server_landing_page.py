# # server.py
# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# import uvicorn
#
# app = FastAPI()
#
# # If you also have API routes like /mcp, define them BEFORE the mount below.
# # from my_mcp_app import mcp_app
# # app.mount("/mcp", mcp_app)
#
# # Serve the entire docs directory at the site root
# # html=True makes / return docs/index.html
# app.mount("/", StaticFiles(directory="docs", html=True), name="docs")
#
# if __name__ == "__main__":
#     print("Serving docs at http://localhost:8000")
#     uvicorn.run(app, host="0.0.0.0", port=8000)


# server.py
import os
from pathlib import Path

from fastmcp import FastMCP
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.requests import Request

mcp = FastMCP(name="1mcpserver", version="0.1.0")
DOCS_DIR = Path(__file__).parent / "docs"


def _file_or_404(p: Path):
    if p.is_file():
        # Add a tiny bit of caching for static assets
        headers = {}
        if any(part == "_next" for part in p.parts):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return FileResponse(p, headers=headers)
    return PlainTextResponse("Not Found", status_code=404)


@mcp.custom_route("/", methods=["GET"])
async def serve_root(_: Request):
    return _file_or_404(DOCS_DIR / "index.html")

@mcp.custom_route("/_next/{rest:path}", methods=["GET"])
async def serve_next(request: Request):
    if request is not None:
        req = request.base_url
        print(f"Got _next request: {req} requesting for url {request.url}")
    rest = request.path_params.get("rest", "")
    print(request.path_params)
    print(f"Serving _next file: {rest}")
    return _file_or_404(DOCS_DIR / f"_next/{rest}")


# Serve any other file that lives under docs/ (images, css, js, favicon, etc.)
# e.g. /assets/logo.png, /robots.txt, /sitemap.xml, /favicon.ico
@mcp.custom_route("/{rest:path}", methods=["GET"])
async def serve_any(request: Request):
    # Try exact file first
    rest = request.path_params.get("rest", "")
    file_resp = _file_or_404(DOCS_DIR / rest)
    if file_resp.status_code == 200:
        return file_resp
    # Optional SPA-style fallback: if you want unknown paths to render index.html
    # (useful if you have client-side routing)
    # return _file_or_404(_safe_path("index.html"))
    return file_resp

if __name__ == "__main__":
    # Run the FastMCP server (includes our custom routes)
    # You can also set host/port via env vars if you like
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))