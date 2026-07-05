from __future__ import annotations

from app.models.insights_coaching import InsightDashboardPayload


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def structured_insight_coaching(payload: InsightDashboardPayload) -> dict:
    """Reshape the generic insight payload into the two client-specified card
    structures (CLAUDE.md 9.5):
      - AI Insight Summary : Key Drivers / Watch Outs / What to Monitor
      - AI Coaching Card   : Recommendation / Shoutout / Action Steps / Guideline Basis
    Deterministic (no extra LLM cost) and grounded ONLY in the payload's cards +
    coaching plan — every element traces back to a real card/evidence item.
    """
    cards = payload.cards or []

    # Key Drivers = the concrete numeric figures behind the picture (dedup by label).
    key_drivers: list[dict] = []
    seen: set[str] = set()
    for card in cards:
        for ev in card.evidence:
            val = _num(ev.value)
            if val is None or ev.title in seen:
                continue
            seen.add(ev.title)
            key_drivers.append({"label": ev.title, "value": ev.value, "detail": ev.detail, "source": ev.source})
    key_drivers = key_drivers[:5]

    # Watch Outs = the High/Medium severity cards, worst first.
    order = {"High": 0, "Medium": 1, "Low": 2}
    watch_outs = [
        {"title": c.title, "summary": c.summary, "severity": c.severity, "confidence": c.confidence}
        for c in sorted(cards, key=lambda c: order.get(c.severity, 3))
        if c.severity in ("High", "Medium")
    ][:4]

    # What to Monitor = the metric names to track over time (distinct evidence titles).
    what_to_monitor: list[str] = []
    for card in cards:
        for ev in card.evidence:
            if _num(ev.value) is not None and ev.title not in what_to_monitor:
                what_to_monitor.append(ev.title)
    what_to_monitor = what_to_monitor[:6]

    avg_conf = round(sum(c.confidence for c in cards) / len(cards), 2) if cards else 0.0

    plan = payload.coaching_plan
    rec_card = next((c for c in cards if getattr(c.card_type, "name", "") == "RECOMMENDATION"), None)
    recommendation = (
        rec_card.summary if rec_card and "No recommendation" not in rec_card.summary
        else (plan.next_best_actions[0] if plan and plan.next_best_actions else "Run the recommendation engine for this advisor.")
    )

    # Shoutout = the strongest favorable driver (largest positive figure among growth/NNM/revenue).
    favorable_keys = ("Revenue LTM", "NNM 3M", "Revenue Growth 3M %", "Managed Revenue %", "KPI On-Track Ratio")
    best = None
    for kd in key_drivers:
        if kd["label"] in favorable_keys:
            v = _num(kd["value"])
            if v is not None and v > 0 and (best is None or v > (_num(best["value"]) or 0)):
                best = kd
    shoutout = (
        f"Recognize strong {best['label']} ({best['value']}) — {best['detail']}."
        if best else "Acknowledge consistent execution this period and reinforce the current focus."
    )

    action_steps = (plan.next_best_actions[:4] if plan else [])
    guideline_basis = {
        "sources": sorted({ev.source for c in cards for ev in c.evidence}),
        "note": (plan.manager_review_notes[0] if plan and plan.manager_review_notes
                 else "Confirm suitability, risk profile and documentation before acting."),
    }

    return {
        "insight": {
            "executive_summary": payload.executive_summary,
            "confidence": avg_conf,
            "key_drivers": key_drivers,
            "watch_outs": watch_outs,
            "what_to_monitor": what_to_monitor,
        },
        "coaching": {
            "tone": plan.tone.value if plan else "Advisor",
            "recommendation": recommendation,
            "shoutout": shoutout,
            "action_steps": action_steps,
            "guideline_basis": guideline_basis,
            "talk_track": (plan.advisor_talk_track if plan else []),
        },
        "cards": [c.model_dump() for c in cards],
    }
