"""DeepEval configuration and shared fixtures.

Provides:
- DeepSeek evaluator model for cost-effective LLM evaluation
- Shared test fixtures for evaluation scenarios
- Common test data and expected outputs
"""

import os
from typing import Any

import pytest

try:
    from deepeval.models import DeepEvalBaseLLM
except ImportError:
    DeepEvalBaseLLM = object  # Allow import when deepeval not installed


class DeepSeekEvaluator(DeepEvalBaseLLM):
    """Custom evaluator using DeepSeek for cost-effective evaluation.

    DeepSeek provides high-quality LLM evaluation at lower cost than
    OpenAI GPT-4, making it suitable for CI/CD pipelines.
    """

    def __init__(self):
        self.model_name = "deepseek-chat"
        self._client = None

    def load_model(self) -> Any:
        """Lazy load the OpenAI-compatible client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com"
            )
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate evaluation response from DeepSeek."""
        client = self.load_model()
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0  # Deterministic for consistent evaluation
        )
        return response.choices[0].message.content or ""

    async def a_generate(self, prompt: str) -> str:
        """Async generation for async test cases."""
        return self.generate(prompt)  # DeepSeek SDK is sync-only

    def get_model_name(self) -> str:
        """Return model name for DeepEval metrics."""
        return self.model_name


@pytest.fixture
def deepeval_model():
    """Provide configured DeepEval model for tests.

    Usage:
        def test_something(deepeval_model):
            metric = AnswerRelevancyMetric(model=deepeval_model)
    """
    return DeepSeekEvaluator()


@pytest.fixture
def sample_cynefin_queries():
    """Sample queries for each Cynefin domain with expected classifications."""
    return [
        {
            "query": "What is 2+2?",
            "expected_domain": "Clear",
            "rationale": "Deterministic, simple lookup with single correct answer"
        },
        {
            "query": "Why did our marketing campaign increase sales by 15%?",
            "expected_domain": "Complicated",
            "rationale": "Causal analysis needed to identify contributing factors"
        },
        {
            "query": "How might customer preferences evolve in the next 5 years?",
            "expected_domain": "Complex",
            "rationale": "Multiple unknowns, emergent behavior, requires exploration"
        },
        {
            "query": "The entire production system just crashed and we don't know why",
            "expected_domain": "Chaotic",
            "rationale": "Crisis situation requiring immediate action"
        },
        {
            "query": "Maybe we should look into something?",
            "expected_domain": "Disorder",
            "rationale": "Unclear query that cannot be classified"
        }
    ]


@pytest.fixture
def uix_evaluation_criteria():
    """CARF UIX standard evaluation criteria from documentation.

    Based on CARF_UIX_INTERACTION_GUIDELINES.md requirements.
    """
    return """Evaluate if the explanation meets CARF UIX standards:
    1. Answers 'Why this?' - explains reasoning behind the recommendation
    2. Answers 'How confident?' - provides uncertainty quantification (percentage, range, or qualitative)
    3. Answers 'Based on what?' - cites data sources or methodology
    4. Uses accessible language for non-experts (avoids jargon without explanation)
    5. Provides actionable next steps when appropriate

    Score 1.0 if all criteria met, 0.8 if 4/5 met, 0.6 if 3/5 met, lower otherwise."""


@pytest.fixture
def mock_chat_service():
    """Mock ChatService for isolated testing."""
    class MockChatService:
        async def chat(self, request):
            class Response:
                message = "Based on our analysis with 85% confidence..."
                confidence = 0.85
            return Response()
    return MockChatService()


# Skip tests if deepeval not installed
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "deepeval: mark test as requiring deepeval package"
    )


def pytest_collection_modifyitems(config, items):
    """Skip deepeval tests if package not installed."""
    try:
        import deepeval  # noqa: F401
    except ImportError:
        skip_deepeval = pytest.mark.skip(reason="deepeval not installed")
        for item in items:
            if "deepeval" in item.keywords or "tests/deepeval" in str(item.fspath):
                item.add_marker(skip_deepeval)
