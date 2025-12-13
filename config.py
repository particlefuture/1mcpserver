import os
from dotenv import load_dotenv

load_dotenv()
GH_TOKEN = os.getenv("GITHUB_TOKEN")

# Constants
HEADER = {
    "Authorization": f"Bearer {GH_TOKEN}",  # use “token” scheme for PAT
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    )
}