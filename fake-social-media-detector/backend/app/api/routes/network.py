from fastapi import APIRouter, HTTPException

from app.analysis.cluster import detect_cluster
from app.analysis.engine import analyze_profile
from app.analysis.network import build_network
from app.schemas.profile import ProfileInput
from app.services.sample_service import get_sample_profile, load_samples, sample_payloads

router = APIRouter(tags=["network"])


@router.get("/network/overview")
def network_overview() -> dict:
    samples = load_samples()
    nodes = []
    edges = []
    for sample in samples:
        profile = sample["profile"]
        nodes.append(
            {
                "id": profile["username"],
                "label": f"@{profile['username']}",
                "group": sample["category"],
                "risk": 20 if sample["category"] == "genuine" else 80 if "scam" in sample["category"] or "bot" in sample["category"] else 55,
            }
        )
    promo = [s["profile"]["username"] for s in samples if s["category"] in {"spam", "scam", "bot"}]
    for username in promo[1:]:
        edges.append({"source": promo[0], "target": username, "relation": "shared-signals"})
    return {
        "title": "Local sample neighborhood",
        "prototype_note": "Generated from bundled samples — not live platform data.",
        "nodes": nodes,
        "edges": edges,
        "clusters": [
            {
                "id": "promo-bot-cluster",
                "size": max(len(promo), 3),
                "members": promo,
                "risk": 82,
                "title": "Potential coordinated cluster detected",
                "explanation": "Promotional, bot, and giveaway samples share keywords, cadence, and low engagement.",
            }
        ],
    }


@router.post("/network/analyze")
def network_for_profile(payload: ProfileInput) -> dict:
    samples = sample_payloads()
    result = analyze_profile(payload, samples)
    return {
        "network": result.network.model_dump(),
        "cluster": result.cluster.model_dump(),
        "impersonation": result.impersonation.model_dump(),
        "fake_probability": result.fake_probability,
    }


@router.get("/network/sample/{sample_id}")
def network_for_sample(sample_id: str) -> dict:
    try:
        profile = get_sample_profile(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0] if exc.args else "Unknown sample") from exc
    samples = sample_payloads()
    cluster = detect_cluster(profile, samples)
    network = build_network(profile, cluster.members, 70 if cluster.detected else 30)
    return {"network": network.model_dump(), "cluster": cluster.model_dump()}
