from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List, Optional
import os
import asyncio

# Import scraper
from app.scrapers import scrape_live_sports

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set in environment")
print("MONGO_URI =", MONGO_URI)

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client["live_dashboard"]

# Initialize FastAPI app
app = FastAPI(title="Live Sports API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SportsMatch(BaseModel):
    match_id: str = Field(..., example="match_12345")
    team_a: str = Field(..., example="Team A")
    team_b: str = Field(..., example="Team B")
    score_a: Optional[int] = Field(None, example=0)
    score_b: Optional[int] = Field(None, example=0)
    status: str = Field(..., example="live")  # live, upcoming, finished
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

# Create indexes for faster queries
async def create_indexes():
    await db.sports_matches.create_index("status")
    await db.sports_matches.create_index("last_updated")
    await db.sports_matches.create_index("match_id", unique=True)

# Background task to scrape and update MongoDB
async def update_mongodb_periodically(interval: int = 300):
    while True:
        try:
            live_matches = await scrape_live_sports()
            for match in live_matches:
                await db.sports_matches.update_one(
                    {"match_id": match["match_id"]},
                    {"$set": match},
                    upsert=True
                )
            print(f"[{datetime.utcnow().isoformat()}] MongoDB updated successfully")
        except Exception as e:
            print(f"Error updating MongoDB: {e}")

        await asyncio.sleep(interval)

# Startup event
@app.on_event("startup")
async def startup_event():
    await create_indexes()
    asyncio.create_task(update_mongodb_periodically(interval=300))  # every 5 minutes

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# Sports endpoints
@app.get("/sports/live")
async def get_live_sports(limit: int = 50):
    cursor = db.sports_matches.find({"status": "live"}).sort("last_updated", -1).limit(limit)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

@app.get("/sports/upcoming")
async def get_upcoming_sports(limit: int = 50):
    cursor = db.sports_matches.find({"status": "upcoming"}).sort("last_updated", -1).limit(limit)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

@app.post("/sports")
async def add_sports_match(match: SportsMatch):
    doc = match.dict()
    doc["last_updated"] = datetime.utcnow()
    result = await db.sports_matches.update_one(
        {"match_id": doc["match_id"]},
        {"$set": doc},
        upsert=True
    )
    if result.upserted_id or result.modified_count > 0:
        return {"ok": True, "message": "Sports match added/updated successfully"}
    raise HTTPException(status_code=500, detail="Failed to add/update sports match")
