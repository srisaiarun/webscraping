import re
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict

async def scrape_live_sports() -> List[Dict]:
    """
    Scrape live and upcoming soccer matches from ESPN's public scoreboard page,
    including team names, scores, status, and team logos.
    """
    url = "https://www.espn.com/soccer/scoreboard"
    matches: List[Dict] = []

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed to fetch scoreboard page: {response.status}")
                return []

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Each match container
            for idx, match_div in enumerate(soup.select(".Scoreboard")):
                try:
                    # Team names
                    teams = match_div.select(".ScoreCell__TeamName")
                    if len(teams) < 2:
                        continue
                    team_a = teams[0].text.strip()
                    team_b = teams[1].text.strip()

                    # Scores
                    scores = match_div.select(".ScoreCell__Score")
                    score_a = int(scores[0].text.strip()) if len(scores) >= 1 and scores[0].text.strip().isdigit() else 0
                    score_b = int(scores[1].text.strip()) if len(scores) >= 2 and scores[1].text.strip().isdigit() else 0

                    # Match status
                    status_div = match_div.select_one(".ScoreboardStatus")
                    status = status_div.text.strip().lower() if status_div else "scheduled"

                    # Team logos (from img inside ScoreCell__Logo)
                    logo_imgs = match_div.select(".ScoreCell__Logo img")
                    logo_a = logo_imgs[0]["src"] if len(logo_imgs) >= 1 else ""
                    logo_b = logo_imgs[1]["src"] if len(logo_imgs) >= 2 else ""

                    # Clean URLs
                    if logo_a and "?" in logo_a:
                        logo_a = logo_a.split("?")[0]
                    if logo_b and "?" in logo_b:
                        logo_b = logo_b.split("?")[0]

                    def slugify(text: str) -> str:
                        """Simple slugify: lowercase, replace non-alphanum with underscore."""
                        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

                    match_id = f"match_{slugify(team_a)}_{slugify(team_b)}"

                    match = {
                        "match_id": match_id,
                        "team_a": team_a,
                        "team_b": team_b,
                        "logo_a": logo_a,
                        "logo_b": logo_b,
                        "score_a": score_a,
                        "score_b": score_b,
                        "status": status,
                        "last_updated": datetime.utcnow()
                    }

                    matches.append(match)
                except Exception as e:
                    print(f"Error parsing match {idx}: {e}")
                    continue

    return matches
