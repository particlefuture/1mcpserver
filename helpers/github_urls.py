from typing import List, Tuple, Optional
import re


API_KEY_PATTERN_RE = re.compile(
    r"\b(?:api[-_ ]?key|apikey|x[-_]api[-_]key)\b",
    re.IGNORECASE
)


def _parse_github_url(url: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
    """
    Parse a GitHub URL to extract owner, repo, branch (if present), and subpath.
    Examples it understands:
     - https://github.com/owner/repo
     - https://github.com/owner/repo/
     - https://github.com/owner/repo/tree/main/path/to/dir
     - https://github.com/owner/repo/blob/main/path/to/README.md
    Returns (owner, repo, branch, subpath) where branch/subpath may be None.
    """
    if "github.com/" not in url:
        return None
    # Remove protocol
    path = url.split("github.com/", 1)[1]
    path = path.strip().rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")

    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    branch = None
    subpath = None
    if len(parts) >= 3:
        kind = parts[2]  # e.g., "tree" or "blob" or something else
        if kind in ("tree", "blob") and len(parts) >= 4:
            branch = parts[3]
            if len(parts) >= 5:
                subpath = "/".join(parts[4:])
        else:
            # Could be direct owner/repo/<something>; treat that as subpath on default branch
            subpath = "/".join(parts[2:])
    return owner, repo, branch, subpath