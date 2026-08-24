# FakeGuard AI — Fake Social Media Account Detector

AI-powered social media authenticity and risk analysis.

This is a **working local prototype** for a college project / hackathon. It estimates whether a social media account looks **genuine, suspicious, or fake** using heuristic feature scoring. It does **not** call Instagram, X, Facebook, TikTok, or LinkedIn APIs, and it never asks for login credentials.

---

## Problem statement

Fake social media accounts are used for:

- Scams
- Spam
- Impersonation
- Fake promotions
- Bot networks
- Phishing
- Misinformation
- Manipulation
- Fraud

Users usually see a username, a photo, a bio, and a follower count. That is not enough to judge whether an account is trustworthy.

## Solution

FakeGuard AI analyzes **many signals together** instead of relying on a single feature:

| Signal | Weight |
| --- | --- |
| Profile completeness | 10% |
| Username risk | 10% |
| Engagement anomaly | 20% |
| Follower / following ratio | 10% |
| Account age | 10% |
| Behavior patterns | 15% |
| Bio risk | 10% |
| Content patterns | 10% |
| Profile image signal | 5% |

Each feature is normalized to 0–100. The weighted sum is the **fake-account probability**. Changing the input data changes the score, charts, reasons, and purpose classification.

---

## Important limitations

This tool provides an estimated risk score based on available profile signals and heuristic analysis. It cannot guarantee that an account is fake or genuine. Real-world accuracy would require large-scale training data, platform APIs, historical behavior, and continuous model validation.

The prototype:

- Analyzes user-supplied or bundled sample data only
- Does not scrape websites
- Does not request social-media passwords
- Does not claim a profile photo proves a real person

---

## Project structure

```text
fake-social-media-detector/
├── backend/app/
│   ├── main.py
│   ├── api/routes/
│   ├── analysis/          # modular scoring engine
│   ├── models/ schemas/ services/ database/ utils/
├── frontend/src/
│   ├── pages/ components/ charts/ services/ hooks/ types/
├── data/samples/
├── requirements.txt
└── README.md
```

---

## Installation

### Backend

Python 3.11+ (3.14 works). From the project root:

```bash
cd fake-social-media-detector
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Frontend

```bash
cd fake-social-media-detector/frontend
npm install
npm run dev
```

UI: [http://localhost:5173](http://localhost:5173)

Optional: copy `.env.example` values. The Vite dev server proxies `/api` to port 8000, so `VITE_API_URL` can stay empty during local development.

---

## Deploy on Vercel

The live UI at a `*.vercel.app` URL is only half the app. If **Launch Demo** fails, Vercel is serving the React frontend but **not** FastAPI. `/api/samples` then returns HTML instead of JSON.

Use **one Vercel project** that builds the UI and the API together.

1. Push these files to GitHub.
2. In Vercel → Project → **Settings → General → Root Directory**.
3. Set Root Directory to `fake-social-media-detector` (**not** `frontend`, **not** `backend`).
   Your GitHub repo root is `Sih`, so this subdirectory is required.
4. Framework preset: **Other**. Build command and output are in `vercel.json`.
5. Redeploy.
6. Check `https://your-app.vercel.app/api/health` — it must return JSON like `{"status":"ok",...}`, not the FakeGuard homepage.

You do **not** need `VITE_API_URL` for this setup. The browser calls `/api` on the same domain.

SQLite history on Vercel is ephemeral (serverless `/tmp`). Analysis still works.

---

## Demo instructions

1. Start backend, then frontend.
2. Open the home page and click **Launch Demo**.
3. Watch the analysis steps, then the results dashboard.
4. Also try **Try Genuine Account** and **Try Suspicious Account**.
5. On Analyzer, load any sample chip, edit followers / likes / bio, and re-analyze — the score must change.
6. Compare two samples on **Compare**.
7. Open **History** to re-open or delete a result and regenerate a report.

---

## Example API request

```bash
curl -s http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "username": "crypto_giveaway_9283",
    "platform": "twitter",
    "followers": 25400,
    "following": 4800,
    "posts": 45,
    "account_age_days": 18,
    "bio": "FREE BITCOIN GIVEAWAY! Send 0.1 ETH get 2 ETH back!",
    "verified": false,
    "average_likes": 80,
    "average_comments": 3
  }'
```

## Example API response (shape)

```json
{
  "username": "crypto_giveaway_9283",
  "fake_probability": 87,
  "risk_level": "Very High Risk",
  "purpose": "Scam/Fraud Risk",
  "purpose_confidence": 41.2,
  "feature_scores": {
    "username": 78,
    "engagement": 92,
    "behavior": 85,
    "bio": 73,
    "content": 89
  },
  "reasons": [],
  "recommendations": []
}
```

Exact numbers depend on the full feature set supplied with the request.

---

## REST API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| GET | `/api/samples` | Bundled demo profiles |
| GET | `/api/samples/{id}` | Full sample payload |
| POST | `/api/analyze` | Analyze a profile JSON body |
| POST | `/api/analyze/upload` | Analyze uploaded JSON (+ optional image) |
| POST | `/api/compare` | Side-by-side analysis |
| GET | `/api/history` | Previous analyses |
| GET | `/api/history/{id}` | Stored result |
| DELETE | `/api/history/{id}` | Delete a result |
| POST | `/api/reports/{analysis_id}?fmt=json\|pdf` | Create a report |
| GET | `/api/reports/{id}/download` | Download JSON or PDF |
| GET | `/api/network/overview` | Sample graph / clusters |

---

## How fake-account scoring works

1. **Feature extraction** — username entropy and digits, bio keywords, engagement rate, follower ratio, age, posting cadence, caption similarity, optional image variance.
2. **Normalization** — every analyzer returns a 0–100 risk score (higher = more suspicious).
3. **Weighted combination** — see the table above. The sum is `fake_probability`.
4. **Risk bands**
   - 0–25 Likely Genuine
   - 26–50 Low Suspicion
   - 51–70 Suspicious
   - 71–85 High Risk
   - 86–100 Very High Risk
5. **Purpose classification** — a second heuristic ranks personal, business, influencer, bot, spam, scam, giveaway, impersonation, political, marketing, or unknown. Top-3 scores are shown as relative estimates.
6. **Explainability** — each reason includes severity, weighted contribution, and a plain-language explanation.

The engine lives in `backend/app/analysis/` so a trained model (Random Forest, XGBoost, etc.) can later replace `scoring.py` without rewriting the API.

---

## Sample accounts

| ID | Type |
| --- | --- |
| `genuine-personal` | Genuine personal |
| `fake-bot` | Fake / bot |
| `spam-account` | Spam |
| `influencer` | Influencer / creator |
| `scam-giveaway` | Scam / giveaway |
| `impersonation` | Possible impersonation |
| `business-brand` | Business / brand |

Upload schema example: `data/samples/example-upload.json`.

---

## Future improvements

- Train a supervised model on labeled account datasets
- NLP transformers for bio / caption intent
- Computer-vision models for profile photos (still not identity proof)
- Graph neural networks for bot-cluster detection
- Authorized platform APIs and historical timelines
- Anomaly detection on longitudinal engagement
- Multi-analyst review workflow and calibration plots
- Stronger impersonation matching against official brand registries

---

## Security notes

- All inputs are validated with Pydantic
- Upload size is capped (JSON 2 MB, image 1 MB)
- Text is length-limited and stripped of control characters
- Passwords and platform cookies are never collected
- Stack traces are not returned to the browser
