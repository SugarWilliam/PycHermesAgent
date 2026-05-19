"""Contract tests for __post_init__ validation on key schema dataclasses."""

import pytest

from pyc_hermes_agent.contracts.schemas import (
    AgentLoopRequest,
    MetaAnalysisRequest,
)


class TestMetaAnalysisRequestValidation:
    def test_empty_problem_statement_raises(self):
        with pytest.raises(ValueError, match="problem_statement must be a non-empty string"):
            MetaAnalysisRequest(problem_statement="")

    def test_whitespace_problem_statement_raises(self):
        with pytest.raises(ValueError, match="problem_statement must be a non-empty string"):
            MetaAnalysisRequest(problem_statement="   ")

    def test_valid_problem_statement(self):
        req = MetaAnalysisRequest(problem_statement="valid")
        assert req.problem_statement == "valid"


class TestAgentLoopRequestValidation:
    def test_invalid_analysis_mode_raises(self):
        with pytest.raises(ValueError, match="analysis_mode must be one of"):
            AgentLoopRequest(analysis_mode="invalid")

    def test_max_iterations_zero_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            AgentLoopRequest(max_iterations=0)

    def test_retry_budget_negative_raises(self):
        with pytest.raises(ValueError, match="retry_budget must be >= 0"):
            AgentLoopRequest(retry_budget=-1)

    def test_defaults_valid(self):
        req = AgentLoopRequest()
        assert req.analysis_mode == "casual"
        assert req.max_iterations == 8
        assert req.retry_budget == 1
