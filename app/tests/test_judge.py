"""Acceptance S8 (machine part): the judge sees receipt evidence only and
returns a structured adopt/reject verdict."""

import json

from runanchor.judge import NemotronJudge, sanitize_evidence


def judge_with(payload, calls=None):
    def fake_post(url, headers, body):
        if calls is not None:
            calls.append(body)
        return payload

    return NemotronJudge(api_key="k", model="judge-model", http_post=fake_post)


EVIDENCE = {
    "task": "fix-sort",
    "command": "pytest -q",
    "exit_code": 0,
    "stdout_tail": "1 passed in 0.4s",
    "diff_sha256": "abc",
}


def test_adopt_verdict():
    payload = {"choices": [{"message": {"content": '{"decision": "adopt", "reason": "tests pass"}'}}]}
    v = judge_with(payload).review(EVIDENCE)
    assert v.decision == "adopt"
    assert v.reason == "tests pass"


def test_reject_verdict():
    payload = {"choices": [{"message": {"content": '{"decision": "reject", "reason": "log looks fake"}'}}]}
    v = judge_with(payload).review(EVIDENCE)
    assert v.decision == "reject"


def test_unparseable_output_defaults_to_reject():
    """A judge that cannot produce a verdict must fail safe — never auto-adopt."""
    payload = {"choices": [{"message": {"content": "I think it is fine"}}]}
    v = judge_with(payload).review(EVIDENCE)
    assert v.decision == "reject"
    assert "unparseable" in v.reason.lower() or "invalid" in v.reason.lower()


def test_invalid_decision_value_defaults_to_reject():
    payload = {"choices": [{"message": {"content": '{"decision": "maybe"}'}}]}
    v = judge_with(payload).review(EVIDENCE)
    assert v.decision == "reject"


def test_reasoning_preface_skipped():
    payload = {"choices": [{"message": {"content": 'analyzing the evidence...\n{"decision": "adopt", "reason": "ok"}'}}]}
    v = judge_with(payload).review(EVIDENCE)
    assert v.decision == "adopt"


def test_evidence_is_sanitized_before_sending():
    """Secret-looking strings must not be shipped to the judge endpoint."""
    calls = []
    payload = {"choices": [{"message": {"content": '{"decision": "adopt", "reason": "ok"}'}}]}
    j = judge_with(payload, calls)
    j.review({**EVIDENCE, "stdout_tail": "token: sk-live1234567890abcdef done"})
    sent = json.dumps(calls[0])
    assert "sk-live1234567890abcdef" not in sent
    assert "REDACTED" in sent


def test_sanitize_evidence_redacts_common_secret_shapes():
    out = sanitize_evidence({"log": "Bearer abc.def.ghi and key=AKIAIOSFODNN7EXAMPLE"})
    assert "AKIAIOSFODNN7EXAMPLE" not in json.dumps(out)
    assert "abc.def.ghi" not in json.dumps(out)
