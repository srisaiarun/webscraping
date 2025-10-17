import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List

async def scrape_live_sports() -> List[dict]:
    """
    Scrape live soccer matches from ESPN.
    Returns a list of dictionaries with match info.
    """
    url = "https://www.espn.com/soccer/scoreboard"
    matches = []

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            for idx, match_div in enumerate(soup.select(".Scoreboard")):  # main match container
                try:
                    teams = match_div.select(".ScoreCell__TeamName")
                    scores = match_div.select(".ScoreCell__Score")

                    if len(teams) < 2 or len(scores) < 2:
                        continue

                    team_a = teams[0].text.strip()
                    team_b = teams[1].text.strip()
                    score_a = int(scores[0].text.strip())
                    score_b = int(scores[1].text.strip())

                    match = {
                        "match_id": f"match_{idx}_{datetime.utcnow().timestamp()}",
                        "team_a": team_a,
                        "team_b": team_b,
                        "score_a": score_a,
                        "score_b": score_b,
                        "status": "live",
                        "last_updated": datetime.utcnow()
                    }
                    matches.append(match)
                except Exception:
                    continue

    return matches
