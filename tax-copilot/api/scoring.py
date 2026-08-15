"""Pure scoring functions -- no DB/HTTP/LLM access. Ported from src/assignment2_judge.py."""

Verdict = str  # "good" | "ok" | "bad"


def latency_rating(latency_ms: float) -> Verdict:
    if latency_ms <= 2000:
        return "good"
    if latency_ms <= 5000:
        return "ok"
    return "bad"


def compute_final_score(
    ratings: dict[str, Verdict],
    pass_bar_min_good: int,
    pass_bar_max_bad: int,
    go_no_go: list[dict],
) -> str:
    """Generalizes assignment2_judge.py's compute_final_score: pass-bar numbers and
    go/no-go rules are parameters instead of hardcoded. go_no_go entries look like
    {"criterion": "Grounding", "fails_unless_good": True} or
    {"criterion": "Length", "fails_if_bad": True}.
    """
    for rule in go_no_go:
        criterion = rule["criterion"]
        verdict = ratings.get(criterion)
        if rule.get("fails_unless_good") and verdict != "good":
            return "fail"
        if rule.get("fails_if_bad") and verdict == "bad":
            return "fail"

    good_count = sum(1 for v in ratings.values() if v == "good")
    bad_count = sum(1 for v in ratings.values() if v == "bad")
    if good_count >= pass_bar_min_good and bad_count <= pass_bar_max_bad:
        return "pass"
    return "fail"


def compute_agreement(
    human_ratings: dict[str, Verdict], judge_ratings: dict[str, Verdict]
) -> dict:
    """Per-criterion match/mismatch for criteria present in both dicts, plus an
    overall agreement rate."""
    shared_criteria = [c for c in human_ratings if c in judge_ratings]

    per_criterion = {}
    match_count = 0
    for criterion in shared_criteria:
        is_match = human_ratings[criterion] == judge_ratings[criterion]
        per_criterion[criterion] = {
            "human": human_ratings[criterion],
            "judge": judge_ratings[criterion],
            "match": is_match,
        }
        if is_match:
            match_count += 1

    agreement_rate = match_count / len(shared_criteria) if shared_criteria else 0.0

    return {
        "per_criterion": per_criterion,
        "agreement_rate": agreement_rate,
        "compared_count": len(shared_criteria),
    }
