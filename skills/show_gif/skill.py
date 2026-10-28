"""
Feature: show_gif
Description: Displays a GIF on the screen based on a user-provided search query.
Requires `GIPHY_API_KEY` environment variable; reports unavailability if missing.
"""

FEATURE_METADATA = {
    "name": "show_gif",
    "aliases": ["display gif", "show animation", "render gif", "showgif"],
    "description": "Displays a GIF on the screen based on a user-provided search query. Requires the `GIPHY_API_KEY` environment variable; if missing, reports that GIF lookup cannot run.",
    "triggers": [
        "show me a gif of", "display animation for", "find a gif about",
        "render gif of", "show a gif on screen", "show gif",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search term or topic for the GIF (e.g., 'happy cat', 'dancing robot').",
            },
        },
        "required": ["query"],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": [],
    "environment_variables": ["GIPHY_API_KEY"],
}


def execute(**kwargs):
    """Displays a GIF based on a user-provided search query."""
    import os
    import urllib.request
    import urllib.parse
    import json

    query = kwargs.get("query", None)

    if not query:
        return {"error": "Please provide a search query for the GIF."}

    api_key = os.environ.get("GIPHY_API_KEY")
    if not api_key:
        return {
            "error": "GIPHY_API_KEY is not set on this machine, so GIF lookup cannot run. Set GIPHY_API_KEY to enable this feature.",
        }

    try:
        search_url = (
            f"https://api.giphy.com/v1/gifs/search?api_key={api_key}"
            f"&q={urllib.parse.quote(query)}&limit=1&rating=g"
        )
        with urllib.request.urlopen(search_url, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data["data"]:
            gif_url = data["data"][0]["images"]["original"]["url"]
            return {
                "gif_url": gif_url,
                "query": query,
                "message": f"Here is a GIF for '{query}'.",
            }
        else:
            return {"error": f"Could not find a GIF for '{query}'. Please try a different search term."}

    except Exception as e:
        return {"error": f"An error occurred while fetching the GIF: {str(e)}"}
