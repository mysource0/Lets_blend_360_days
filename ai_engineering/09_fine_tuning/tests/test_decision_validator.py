import json

import pytest

from src.decision_validator import validate_decision_card, validate_submission


def submission(**changes):
    value = {
        "scenario_id": "S01", "selected_architecture": "PROMPT_CONTEXT",
        "reasoning": "Use a prompt and schema for the format transformation.",
        "rejected_alternative": "FINE_TUNING", "discovery_question": "Which fields define quality?",
        "validation_plan": "Test representative notes and schema validity.",
    }
    value.update(changes)
    return value


def test_invalid_architecture_is_rejected():
    with pytest.raises(ValueError, match="must be one of"):
        validate_submission(submission(selected_architecture="MAGIC"))


def test_rejected_alternative_must_be_valid_and_different():
    with pytest.raises(ValueError, match="must be one of"):
        validate_submission(submission(rejected_alternative="MAGIC"))
    with pytest.raises(ValueError, match="must differ"):
        validate_submission(submission(rejected_alternative="PROMPT_CONTEXT"))


def test_incomplete_submission_is_rejected():
    value = submission()
    del value["reasoning"]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_submission(value)


def test_incomplete_decision_card_is_rejected():
    cards = json.loads(open("data/reference_decision_cards.json", encoding="utf-8").read())
    card = cards[0]
    del card["business_outcome"]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_decision_card(card)


def test_scenario_8_requires_deferred_decision():
    with pytest.raises(ValueError, match="DECISION_DEFERRED"):
        validate_submission(submission(scenario_id="S08", selected_architecture="FINE_TUNING", rejected_alternative="PROMPT_CONTEXT"))
    assert validate_submission(submission(scenario_id="S08", selected_architecture="DECISION_DEFERRED", rejected_alternative="PROMPT_CONTEXT"))


def test_scenario_6_requires_staged_approach():
    with pytest.raises(ValueError, match="staged_approach"):
        validate_submission(submission(scenario_id="S06", selected_architecture="COMBINATION"))

