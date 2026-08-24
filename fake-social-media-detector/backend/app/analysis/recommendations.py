"""Actionable recommendations based on the estimated risk band."""


def build_recommendations(probability: float, risk_level: str) -> list[dict]:
    shared = [
        {
            "title": "Automated scores are estimates",
            "detail": "Heuristic analysis cannot guarantee that an account is fake or genuine.",
            "priority": "info",
        }
    ]
    if probability >= 71:
        return [
            {
                "title": "Do not share sensitive information",
                "detail": "Avoid sending OTPs, IDs, payment details, or private photos to this account.",
                "priority": "high",
            },
            {
                "title": "Avoid clicking unexpected links",
                "detail": "Promotional or urgency links are a common phishing path.",
                "priority": "high",
            },
            {
                "title": "Verify through another channel",
                "detail": "Confirm identity via a known website, official handle, or out-of-band contact.",
                "priority": "high",
            },
            {
                "title": "Review account history",
                "detail": "Check creation date, username changes, and sudden follower jumps.",
                "priority": "medium",
            },
            {
                "title": "Report or block if appropriate",
                "detail": "Use the platform reporting tools if the account solicits money or impersonates someone.",
                "priority": "medium",
            },
            *shared,
        ]
    if probability >= 51:
        return [
            {
                "title": "Treat interactions cautiously",
                "detail": f"Risk band is {risk_level}. Ask for corroborating evidence before trusting claims.",
                "priority": "medium",
            },
            {
                "title": "Inspect engagement quality",
                "detail": "Look for generic comments, sudden spikes, or audience/size mismatch.",
                "priority": "medium",
            },
            {
                "title": "Check username and bio language",
                "detail": "Promotional or impersonation phrasing is a useful extra signal.",
                "priority": "low",
            },
            *shared,
        ]
    return [
        {
            "title": "Signals look mostly ordinary",
            "detail": "The profile shows mostly normal characteristics, but automated detection cannot guarantee authenticity.",
            "priority": "low",
        },
        {
            "title": "Still verify high-stakes requests",
            "detail": "Even likely-genuine accounts can be compromised. Confirm payments and identity offline.",
            "priority": "medium",
        },
        *shared,
    ]
