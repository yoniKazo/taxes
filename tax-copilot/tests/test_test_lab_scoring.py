"""Tests for api/scoring.py -- pure functions, no DB/HTTP/LLM access."""

from api.scoring import compute_agreement, compute_final_score, latency_rating

GO_NO_GO = [
    {"criterion": "Grounding", "fails_unless_good": True},
    {"criterion": "Length", "fails_if_bad": True},
]


def _ratings(**overrides) -> dict[str, str]:
    base = {
        "Fluency": "good",
        "Grammar": "good",
        "Tone": "good",
        "Length": "good",
        "Grounding": "good",
        "Latency": "good",
    }
    base.update(overrides)
    return base


class TestComputeFinalScore:
    def test_four_good_zero_bad_passes(self):
        ratings = _ratings(Tone="ok", Latency="ok")  # 4 good, 0 bad
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "pass"

    def test_three_good_fails(self):
        ratings = _ratings(Tone="ok", Latency="ok", Fluency="ok")  # 3 good
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "fail"

    def test_go_no_go_grounding_ok_fails_even_with_five_good(self):
        ratings = _ratings(Grounding="ok")  # 5 good, 1 ok -- would otherwise pass
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "fail"

    def test_go_no_go_length_bad_fails_even_with_all_else_good(self):
        ratings = _ratings(Length="bad")
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "fail"

    def test_any_bad_fails_pass_bar(self):
        ratings = _ratings(Fluency="bad")  # 5 good, 1 bad -- bad_count exceeds max_bad
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "fail"

    def test_all_good_passes(self):
        ratings = _ratings()
        assert compute_final_score(ratings, 4, 0, GO_NO_GO) == "pass"


class TestLatencyRating:
    def test_2000ms_is_good(self):
        assert latency_rating(2000) == "good"

    def test_2001ms_is_ok(self):
        assert latency_rating(2001) == "ok"

    def test_5000ms_is_ok(self):
        assert latency_rating(5000) == "ok"

    def test_5001ms_is_bad(self):
        assert latency_rating(5001) == "bad"


class TestComputeAgreement:
    def test_known_agreement_rate(self):
        human = {
            "Fluency": "good",
            "Grammar": "good",
            "Tone": "ok",
            "Length": "good",
            "Grounding": "good",
        }
        judge = {
            "Fluency": "good",   # match
            "Grammar": "ok",     # mismatch
            "Tone": "bad",       # mismatch
            "Length": "good",    # match
            "Grounding": "good",  # match
        }
        result = compute_agreement(human, judge)
        assert result["compared_count"] == 5
        assert result["agreement_rate"] == 3 / 5
        assert result["per_criterion"]["Fluency"]["match"] is True
        assert result["per_criterion"]["Grammar"]["match"] is False
        assert result["per_criterion"]["Tone"] == {
            "human": "ok",
            "judge": "bad",
            "match": False,
        }

    def test_only_shared_criteria_are_compared(self):
        human = {"Fluency": "good", "Grammar": "good"}
        judge = {"Fluency": "good", "Tone": "good"}
        result = compute_agreement(human, judge)
        assert result["compared_count"] == 1
        assert result["agreement_rate"] == 1.0

    def test_empty_overlap_gives_zero_rate(self):
        result = compute_agreement({"Fluency": "good"}, {"Tone": "good"})
        assert result["compared_count"] == 0
        assert result["agreement_rate"] == 0.0
