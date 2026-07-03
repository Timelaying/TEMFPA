"""Key factor derivation and narrative generation for predictions."""

from __future__ import annotations


def derive_key_factors(
    feature_vector: dict,
    probs: dict,
    home_team_name: str,
    away_team_name: str,
) -> list[dict]:
    """Analyze feature vector and produce up to 6 human-readable factor dicts.

    Each factor: {"factor": str, "description": str, "impact": str, "direction": str}
    impact: "positive" | "negative" | "neutral"
    direction: "home" | "away" | "neutral"
    """
    factors = []

    home_wr5 = feature_vector.get("home_win_rate_5", 0.5)
    away_wr5 = feature_vector.get("away_win_rate_5", 0.5)
    home_gs5 = feature_vector.get("home_goals_scored_5", 1.0)
    away_gs5 = feature_vector.get("away_goals_scored_5", 1.0)
    home_gc5 = feature_vector.get("home_goals_conceded_5", 1.0)
    away_gc5 = feature_vector.get("away_goals_conceded_5", 1.0)
    home_absence = feature_vector.get("home_absence_penalty", 0.0)
    away_absence = feature_vector.get("away_absence_penalty", 0.0)
    h2h_home_wr = feature_vector.get("h2h_home_win_rate", 0.5)
    h2h_away_wr = feature_vector.get("h2h_away_win_rate", 0.25)
    h2h_total = feature_vector.get("h2h_total", 0)

    # --- Home form ---
    if home_wr5 > 0.6:
        wins = round(home_wr5 * 5)
        factors.append({
            "factor": "home_form",
            "description": f"{home_team_name} in excellent recent form ({wins} wins in last 5)",
            "impact": "positive",
            "direction": "home",
        })
    elif home_wr5 < 0.3:
        factors.append({
            "factor": "home_form",
            "description": f"{home_team_name} in poor recent form",
            "impact": "negative",
            "direction": "home",
        })

    # --- Away form ---
    if away_wr5 > 0.6:
        wins = round(away_wr5 * 5)
        factors.append({
            "factor": "away_form",
            "description": f"{away_team_name} in excellent recent form ({wins} wins in last 5)",
            "impact": "positive",
            "direction": "away",
        })
    elif away_wr5 < 0.3:
        factors.append({
            "factor": "away_form",
            "description": f"{away_team_name} in poor recent form",
            "impact": "negative",
            "direction": "away",
        })

    # --- Home goals scored ---
    if home_gs5 > 2.0:
        factors.append({
            "factor": "home_attack",
            "description": f"{home_team_name} averaging {home_gs5:.1f} goals per game",
            "impact": "positive",
            "direction": "home",
        })

    # --- Away goals scored ---
    if away_gs5 > 2.0:
        factors.append({
            "factor": "away_attack",
            "description": f"{away_team_name} averaging {away_gs5:.1f} goals per game",
            "impact": "positive",
            "direction": "away",
        })

    # --- Home defence ---
    if home_gc5 < 0.8:
        factors.append({
            "factor": "home_defence",
            "description": f"{home_team_name} has a solid defence (conceding {home_gc5:.1f} per game)",
            "impact": "positive",
            "direction": "home",
        })

    # --- Away defence ---
    if away_gc5 < 0.8:
        factors.append({
            "factor": "away_defence",
            "description": f"{away_team_name} has a solid defence (conceding {away_gc5:.1f} per game)",
            "impact": "positive",
            "direction": "away",
        })

    # --- Absences ---
    if home_absence > 0.05:
        factors.append({
            "factor": "home_absences",
            "description": f"{home_team_name} missing key player(s)",
            "impact": "negative",
            "direction": "home",
        })

    if away_absence > 0.05:
        factors.append({
            "factor": "away_absences",
            "description": f"{away_team_name} missing key player(s)",
            "impact": "negative",
            "direction": "away",
        })

    # --- H2H ---
    if h2h_total < 3:
        factors.append({
            "factor": "h2h_limited",
            "description": "Limited head-to-head history available",
            "impact": "neutral",
            "direction": "neutral",
        })
    else:
        if h2h_home_wr > 0.6:
            factors.append({
                "factor": "h2h_dominance",
                "description": f"{home_team_name} dominates this fixture historically",
                "impact": "positive",
                "direction": "home",
            })
        elif h2h_away_wr > 0.6:
            factors.append({
                "factor": "h2h_dominance",
                "description": f"{away_team_name} dominates this fixture historically",
                "impact": "positive",
                "direction": "away",
            })

    return factors[:6]


def build_narrative(
    key_factors: list[dict],
    home_team: str,
    away_team: str,
    result: str,
    confidence: str,
) -> str:
    """Build a single paragraph narrative from key factors and prediction."""
    result_display = {
        "home": f"{home_team} to win",
        "draw": "a draw",
        "away": f"{away_team} to win",
    }.get(result, result)

    narrative_parts = [
        f"Our model predicts {result_display} with {confidence.lower()} confidence."
    ]

    if key_factors:
        positive_home = [f for f in key_factors if f["impact"] == "positive" and f["direction"] == "home"]
        positive_away = [f for f in key_factors if f["impact"] == "positive" and f["direction"] == "away"]
        negative_home = [f for f in key_factors if f["impact"] == "negative" and f["direction"] == "home"]
        negative_away = [f for f in key_factors if f["impact"] == "negative" and f["direction"] == "away"]

        if positive_home:
            narrative_parts.append(
                f"{home_team}'s strengths include: "
                + "; ".join(f["description"] for f in positive_home[:2]) + "."
            )
        if positive_away:
            narrative_parts.append(
                f"{away_team}'s strengths include: "
                + "; ".join(f["description"] for f in positive_away[:2]) + "."
            )
        if negative_home:
            narrative_parts.append(
                f"Concerns for {home_team}: "
                + "; ".join(f["description"] for f in negative_home[:1]) + "."
            )
        if negative_away:
            narrative_parts.append(
                f"Concerns for {away_team}: "
                + "; ".join(f["description"] for f in negative_away[:1]) + "."
            )

        neutral = [f for f in key_factors if f["direction"] == "neutral"]
        if neutral:
            narrative_parts.append(neutral[0]["description"] + ".")

    return " ".join(narrative_parts)
