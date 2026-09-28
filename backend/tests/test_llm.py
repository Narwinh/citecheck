from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.agents.llm import add_usage, structured, usage_from


class FakeModel:
    def __init__(self, name: str, fail: bool):
        self.name, self.fail, self.calls = name, fail, 0

    def with_structured_output(self, schema, include_raw):
        def run(prompt):
            self.calls += 1
            if self.fail:
                raise RuntimeError("503 UNAVAILABLE")
            raw = AIMessage(content="{}", response_metadata={"model_name": self.name})
            return {"raw": raw, "parsed": "ok", "parsing_error": None}

        return RunnableLambda(run)


def test_fallback_model_used_when_primary_fails():
    primary, backup = FakeModel("primary", fail=True), FakeModel("backup", fail=False)
    result = structured([primary, backup], schema=None).invoke("hi")
    assert result["parsed"] == "ok"
    assert (primary.calls, backup.calls) == (1, 1)
    assert usage_from(result["raw"])["calls:backup"] == 1


def test_fallback_not_called_when_primary_works():
    primary, backup = FakeModel("primary", fail=False), FakeModel("backup", fail=False)
    structured([primary, backup], schema=None).invoke("hi")
    assert backup.calls == 0


def test_all_models_failing_keeps_every_error():
    import pytest

    from app.agents.llm import AllModelsFailed

    a, b = FakeModel("a", fail=True), FakeModel("b", fail=True)
    with pytest.raises(AllModelsFailed) as info:
        structured([a, b], schema=None).invoke("hi")
    assert len(info.value.errors) == 2
    assert not info.value.daily_quota_exhausted


def test_daily_quota_detection():
    from app.agents.llm import AllModelsFailed

    quota = RuntimeError("429 RESOURCE_EXHAUSTED ... GenerateRequestsPerDayPerProjectPerModel")
    overload = RuntimeError("503 UNAVAILABLE high demand")
    assert AllModelsFailed([quota, quota]).daily_quota_exhausted
    assert not AllModelsFailed([quota, overload]).daily_quota_exhausted


def test_describe_error_is_short_and_names_the_model():
    from app.agents.llm import describe_error

    quota = RuntimeError(
        "Error calling model 'gemini-3.8-flash' (RESOURCE_EXHAUSTED): 429 ... PerDayPerProject"
    )
    assert describe_error(quota) == "gemini-3.8-flash: 429 per-day quota"
    assert describe_error(RuntimeError("503 UNAVAILABLE high demand")) == "503 overloaded"


def test_add_usage_sums_all_keys():
    total = add_usage({"total_tokens": 5, "calls:a": 1}, {"total_tokens": 3, "calls:b": 1})
    assert total == {"total_tokens": 8, "calls:a": 1, "calls:b": 1}
