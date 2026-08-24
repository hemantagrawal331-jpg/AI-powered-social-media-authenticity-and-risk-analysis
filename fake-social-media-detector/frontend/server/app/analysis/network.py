"""Prototype social-graph generator from local sample relationships."""

from __future__ import annotations

from app.schemas.analysis import NetworkEdge, NetworkInfo, NetworkNode
from app.schemas.profile import ProfileInput


def build_network(profile: ProfileInput, cluster_members: list[str], fake_probability: float) -> NetworkInfo:
    username = profile.username
    nodes = [
        NetworkNode(id=username, label=f"@{username}", group="account", risk=fake_probability),
        NetworkNode(id="followers", label="Followers", group="followers", risk=max(20, fake_probability - 15)),
        NetworkNode(id="following", label="Following", group="following", risk=max(18, fake_probability - 20)),
        NetworkNode(id="similar", label="Similar accounts", group="similar", risk=55),
        NetworkNode(id="suspicious", label="Suspicious accounts", group="suspicious", risk=78),
        NetworkNode(id="bots", label="Potential bot cluster", group="bots", risk=82),
    ]
    edges = [
        NetworkEdge(source=username, target="followers", relation="audience"),
        NetworkEdge(source=username, target="following", relation="follows"),
        NetworkEdge(source=username, target="similar", relation="similar"),
        NetworkEdge(source=username, target="suspicious", relation="shared-signals"),
        NetworkEdge(source="suspicious", target="bots", relation="cluster"),
    ]
    for member in cluster_members[:6]:
        node_id = f"peer-{member}"
        nodes.append(NetworkNode(id=node_id, label=f"@{member}", group="cluster", risk=70))
        edges.append(NetworkEdge(source="bots", target=node_id, relation="coordinated"))

    if fake_probability >= 70:
        risk, explanation = (
            "High",
            "Account appears connected to multiple low-engagement or promotional profiles in the local sample graph.",
        )
    elif fake_probability >= 45:
        risk, explanation = (
            "Moderate",
            "Some neighborhood overlap with promotional or low-engagement sample accounts.",
        )
    else:
        risk, explanation = (
            "Low",
            "Local prototype graph does not show a dense suspicious neighborhood.",
        )

    return NetworkInfo(risk=risk, explanation=explanation, nodes=nodes, edges=edges)
