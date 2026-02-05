"""CARF Test Script - Run this to test the cognitive pipeline.

Usage:
    python test_carf.py
"""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def test_llm_config():
    """Test 1: Verify LLM configuration."""
    print("\n" + "="*60)
    print("TEST 1: LLM Configuration")
    print("="*60)

    from src.core.llm import get_llm_config, get_chat_model
    from langchain_core.messages import HumanMessage

    config = get_llm_config()
    print(f"Provider: {config.provider.value}")
    print(f"Model: {config.model}")
    print(f"Base URL: {config.base_url}")
    print(f"API Key set: {'Yes' if config.api_key else 'No'}")

    if not config.api_key:
        print("ERROR: No API key found. Set DEEPSEEK_API_KEY in .env")
        return False

    # Test LLM call
    print("\nTesting LLM connection...")
    llm = get_chat_model(temperature=0.1, purpose="test")
    response = await llm.ainvoke([HumanMessage(content="Say 'CARF operational' if you can read this.")])
    print(f"LLM Response: {response.content}")

    return "operational" in response.content.lower()


async def test_router():
    """Test 2: Cynefin Router classification."""
    print("\n" + "="*60)
    print("TEST 2: Cynefin Router")
    print("="*60)

    from src.workflows.router import CynefinRouter
    from src.core.state import EpistemicState

    router = CynefinRouter()

    test_cases = [
        ("What is 2 + 2?", "Clear"),
        ("Why did our server costs increase by 15%?", "Complicated"),
        ("How will users react to our new pricing?", "Complex"),
    ]

    results = []
    for query, expected in test_cases:
        state = EpistemicState(user_input=query)
        result = await router.classify(state)

        status = "[OK]" if result.cynefin_domain.value == expected else "[?]"
        print(f"\n{status} Query: '{query}'")
        print(f"  Expected: {expected}")
        print(f"  Got: {result.cynefin_domain.value} (conf: {result.domain_confidence:.2f})")
        results.append(result.cynefin_domain.value)

    return True


async def test_causal_engine():
    """Test 3: Causal Inference Engine."""
    print("\n" + "="*60)
    print("TEST 3: Causal Inference Engine")
    print("="*60)

    from src.services.causal import CausalInferenceEngine

    engine = CausalInferenceEngine()

    query = "Customer churn increased after we raised prices. What's the root cause?"
    print(f"\nQuery: {query}")

    result, graph = await engine.analyze(query)

    print(f"\nHypothesis: {result.hypothesis.treatment} -> {result.hypothesis.outcome}")
    print(f"Mechanism: {result.hypothesis.mechanism}")
    print(f"Effect Size: {result.effect_estimate:.2f}")
    print(f"Confidence Interval: {result.confidence_interval}")
    print(f"Refutation Passed: {result.passed_refutation}")
    print(f"\nInterpretation: {result.interpretation[:200]}...")

    return True


async def test_bayesian_engine():
    """Test 4: Bayesian Active Inference."""
    print("\n" + "="*60)
    print("TEST 4: Bayesian Active Inference")
    print("="*60)

    from src.services.bayesian import ActiveInferenceEngine

    engine = ActiveInferenceEngine()

    query = "Should we expand into the European market? High uncertainty about regulations."
    print(f"\nQuery: {query}")

    result = await engine.explore(query)

    print(f"\nInitial Uncertainty: {result.uncertainty_before:.0%}")
    print(f"Updated Uncertainty: {result.uncertainty_after:.0%}")
    print(f"\nPrimary Hypothesis: {result.updated_belief.hypothesis}")
    print(f"Confidence: {result.updated_belief.posterior:.0%}")

    print(f"\nDesigned {len(result.probes_designed)} probes:")
    for probe in result.probes_designed[:3]:
        print(f"  - {probe.description} (Info Gain: {probe.expected_information_gain:.0%})")

    if result.recommended_probe:
        print(f"\nRecommended: {result.recommended_probe.description}")

    return True


async def test_full_pipeline():
    """Test 5: Full CARF Pipeline."""
    print("\n" + "="*60)
    print("TEST 5: Full CARF Pipeline")
    print("="*60)

    from src.workflows.graph import run_carf

    queries = [
        "What is the capital of France?",
        "Why did our conversion rate drop after the website redesign?",
    ]

    for query in queries:
        print(f"\n{'-'*50}")
        print(f"Query: {query}")

        result = await run_carf(query)

        print(f"Domain: {result.cynefin_domain.value}")
        print(f"Confidence: {result.domain_confidence:.2f}")
        print(f"Guardian: {result.guardian_verdict.value if result.guardian_verdict else 'N/A'}")

        print(f"\nReasoning Chain:")
        for step in result.reasoning_chain:
            print(f"  [{step.node_name}] {step.action}")

        if result.final_response:
            preview = result.final_response[:150].replace('\n', ' ')
            print(f"\nResponse: {preview}...")

    return True


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CARF - Complex-Adaptive Reasoning Fabric")
    print("Phase 2 Test Suite")
    print("="*60)

    tests = [
        ("LLM Config", test_llm_config),
        ("Router", test_router),
        ("Causal Engine", test_causal_engine),
        ("Bayesian Engine", test_bayesian_engine),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = []
    for name, test_fn in tests:
        try:
            success = await test_fn()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\nERROR in {name}: {e}")
            results.append((name, "ERROR"))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, status in results:
        icon = "[OK]" if status == "PASS" else "[X]"
        print(f"  {icon} {name}: {status}")

    print("\n" + "="*60)
    print("Tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
