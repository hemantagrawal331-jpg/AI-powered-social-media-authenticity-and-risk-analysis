"""
FastAPI backend for the Fake Social Media Account Detector.
Run with: uvicorn main:app --reload --port 8000  (from the backend/ folder)
"""
import pickle
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "model" / "rf_model.pkl"
FRONTEND_DIR = BASE_DIR / "frontend"
FEATURES = [
    "followers", "following", "posts", "account_age_days",
    "has_profile_pic", "has_bio", "username_length",
    "username_digit_ratio", "followers_following_ratio",
    "posts_per_day", "is_verified",
]

app = FastAPI(title="Fake Account Detector API")

# Allow the frontend (served from file:// or another port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


class ProfileInput(BaseModel):
    followers: int = Field(..., ge=0)
    following: int = Field(..., ge=1)
    posts: int = Field(..., ge=0)
    account_age_days: int = Field(..., ge=1)
    has_profile_pic: bool
    has_bio: bool
    username_length: int = Field(..., ge=1)
    username_digit_ratio: float = Field(..., ge=0, le=1)
    is_verified: bool = False


def build_reasons(row: dict, proba_fake: float) -> list[str]:
    reasons = []
    ff_ratio = row["followers_following_ratio"]
    if ff_ratio < 0.1:
        reasons.append("Very low followers-to-following ratio")
    if row["account_age_days"] < 60:
        reasons.append("Very new account (under 60 days old)")
    if row["posts_per_day"] < 0.05 and row["account_age_days"] > 30:
        reasons.append("Almost no posting activity")
    if row["username_digit_ratio"] > 0.3:
        reasons.append("Username contains many random digits")
    if not row["has_profile_pic"]:
        reasons.append("No profile picture")
    if not row["has_bio"]:
        reasons.append("Empty bio")
    if not reasons and proba_fake > 0.5:
        reasons.append("Overall pattern of features matches known fake accounts")
    if not reasons:
        reasons.append("Profile metrics fall within typical genuine-account ranges")
    return reasons


@app.get("/api")
def api_status():
    return {"status": "ok", "message": "Fake Account Detector API is running"}


@app.post("/predict")
def predict(profile: ProfileInput):
    following = max(profile.following, 1)
    age = max(profile.account_age_days, 1)
    ff_ratio = profile.followers / following
    posts_per_day = profile.posts / age

    row = {
        "followers": profile.followers,
        "following": following,
        "posts": profile.posts,
        "account_age_days": age,
        "has_profile_pic": int(profile.has_profile_pic),
        "has_bio": int(profile.has_bio),
        "username_length": profile.username_length,
        "username_digit_ratio": profile.username_digit_ratio,
        "followers_following_ratio": round(ff_ratio, 4),
        "posts_per_day": round(posts_per_day, 4),
        "is_verified": int(profile.is_verified),
    }

    X = np.array([[row[f] for f in FEATURES]])
    proba_fake = float(model.predict_proba(X)[0][1])
    prediction = "FAKE" if proba_fake >= 0.5 else "GENUINE"

    return {
        "prediction": prediction,
        "confidence_percent": round(
            proba_fake * 100 if prediction == "FAKE" else (1 - proba_fake) * 100, 2
        ),
        "fake_probability": round(proba_fake, 4),
        "reasons": build_reasons(row, proba_fake),
    }


# Serve the frontend (index.html, etc.) at the root path.
# Must be mounted last so it doesn't shadow the /predict and /api routes above.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
