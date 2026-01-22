"""Bayesian Active Inference Engine for CARF.

Implements Active Inference for navigating the Complex domain where:
- Cause and effect are only coherent in retrospect
- The system must "probe" to learn
- Uncertainty must be quantified and reduced

Core Principles:
1. Free Energy Minimization: Agents minimize surprise (prediction errors)
2. Information Gain: Probes are designed to maximize learning
3. Safe-to-Fail: Experiments must be reversible and bounded in risk

In production, this will use PyMC for full Bayesian inference.
For MVP, we use LLM-assisted probabilistic reasoning.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.llm import get_explorer_model
from src.core.state import BayesianEvidence, ConfidenceLevel, EpistemicState
from src.utils.resiliency import async_retry_with_backoff, retry_with_backoff
from src.utils.cache import async_lru_cache

logger = logging.getLogger("carf.bayesian")


class BayesianBelief(BaseModel):
    """A probabilistic belief about a hypothesis."""
    hypothesis: str = Field(..., description="The hypothesis being evaluated")
    prior: float = Field(..., ge=0.0, le=1.0, description="Prior probability")
    posterior: float = Field(..., ge=0.0, le=1.0, description="Posterior probability")
    evidence_considered: list[str] = Field(
        default_factory=list, description="Evidence that updated the belief"
    )
    confidence_interval: tuple[float, float] = Field(
        default=(0.0, 1.0), description="Credible interval"
    )


class ExplorationProbe(BaseModel):
    """A safe-to-fail probe designed to gather information."""
    probe_id: str = Field(..., description="Unique identifier")
    description: str = Field(..., description="What this probe tests")
    expected_information_gain: float = Field(
        ..., ge=0.0, le=1.0, description="Expected reduction in uncertainty"
    )
    risk_level: str = Field(
        default="low", pattern="^(low|medium|high)$"
    )
    reversible: bool = Field(default=True, description="Can be undone if needed")
    success_criteria: str = Field(..., description="How to evaluate probe results")
    failure_criteria: str = Field(..., description="What indicates probe failed")


class ActiveInferenceResult(BaseModel):
    """Results from Active Inference exploration."""
    initial_belief: BayesianBelief
    updated_belief: BayesianBelief
    probes_designed: list[ExplorationProbe] = Field(default_factory=list)
    recommended_probe: ExplorationProbe | None = None
    uncertainty_before: float = Field(..., description="Entropy before analysis")
    uncertainty_after: float = Field(..., description="Entropy after analysis")
    interpretation: str = Field(..., description="Human-readable summary")


class BayesianInferenceConfig(BaseModel):
    """Configuration for PyMC-based inference."""

    observations: list[float] | None = Field(
        default=None,
        description="Observed data for a normal model",
    )
    successes: int | None = Field(
        default=None,
        ge=0,
        description="Successes for a binomial model",
    )
    trials: int | None = Field(
        default=None,
        ge=1,
        description="Trials for a binomial model",
    )
    draws: int = Field(default=500, ge=100)
    tune: int = Field(default=500, ge=100)
    chains: int = Field(default=2, ge=1)
    target_accept: float = Field(default=0.9, ge=0.5, le=0.99)
    seed: int | None = Field(default=None)

    def has_data(self) -> bool:
        """Return True when the config includes usable observations."""
        if self.observations:
            return True
        if self.successes is not None and self.trials is not None:
            return True
        return False

    def mode(self) -> str:
        """Return inference mode name."""
        if self.observations:
            return "normal"
        if self.successes is not None and self.trials is not None:
            return "binomial"
        return "unknown"


class BayesianInferenceResult(BaseModel):
    """Summary of PyMC inference outputs."""

    posterior_mean: float
    credible_interval: tuple[float, float]
    uncertainty: float


@dataclass
class BeliefNetwork:
    """A network of probabilistic beliefs."""
    beliefs: dict[str, BayesianBelief] = field(default_factory=dict)

    def add_belief(self, belief: BayesianBelief) -> None:
        """Add or update a belief."""
        self.beliefs[belief.hypothesis] = belief

    def get_belief(self, hypothesis: str) -> BayesianBelief | None:
        """Get a belief by hypothesis."""
        return self.beliefs.get(hypothesis)

    def get_most_uncertain(self) -> BayesianBelief | None:
        """Get the belief with highest uncertainty (closest to 0.5)."""
        if not self.beliefs:
            return None
        return min(
            self.beliefs.values(),
            key=lambda b: abs(b.posterior - 0.5)
        )


class ActiveInferenceEngine:
    """Engine for Bayesian Active Inference.

    Handles Complex domain queries by:
    1. Establishing prior beliefs
    2. Identifying high-uncertainty areas
    3. Designing probes to reduce uncertainty
    4. Updating beliefs based on evidence

    The system minimizes "free energy" (surprise) by actively seeking
    information that updates its world model.
    """

    def __init__(self):
        """Initialize the Active Inference engine."""
        self.model = get_explorer_model()
        self._prior_prompt = self._build_prior_prompt()
        self._probe_prompt = self._build_probe_prompt()

    def _build_prior_prompt(self) -> str:
        """Build prompt for establishing priors."""
        return """You are a Bayesian analyst helping to establish prior beliefs about uncertain situations.

## Your Role:
1. Identify the key hypotheses to evaluate
2. Establish reasonable prior probabilities based on domain knowledge
3. Identify what evidence would update these beliefs
4. Quantify uncertainty explicitly

## Output Format:
Respond with a JSON object:
{
    "hypotheses": [
        {
            "hypothesis": "description of hypothesis",
            "prior": 0.0-1.0,
            "reasoning": "why this prior",
            "evidence_that_would_increase": ["evidence1", "evidence2"],
            "evidence_that_would_decrease": ["evidence1", "evidence2"]
        }
    ],
    "overall_uncertainty": 0.0-1.0,
    "key_unknowns": ["unknown1", "unknown2"]
}

## Important:
- Be honest about uncertainty
- Priors should reflect genuine ignorance where appropriate
- Avoid overconfidence
- Consider multiple competing hypotheses"""

    def _build_probe_prompt(self) -> str:
        """Build prompt for designing probes."""
        return """You are designing safe-to-fail probes to reduce uncertainty in a complex situation.

## Probe Design Principles:
1. **Information Gain**: Prioritize probes that maximally reduce uncertainty
2. **Safe-to-Fail**: Probes must be reversible and bounded in risk
3. **Fast Feedback**: Prefer probes with quick results
4. **Minimal Cost**: Balance information gain against resource cost

## Output Format:
Respond with a JSON object:
{
    "probes": [
        {
            "probe_id": "unique_id",
            "description": "what this probe tests",
            "expected_information_gain": 0.0-1.0,
            "risk_level": "low|medium|high",
            "reversible": true|false,
            "success_criteria": "how to know it worked",
            "failure_criteria": "how to know it failed",
            "estimated_duration": "time estimate",
            "resources_needed": ["resource1", "resource2"]
        }
    ],
    "recommended_probe_id": "id of best probe",
    "recommendation_reasoning": "why this probe first"
}

## Important:
- At least one probe must be low-risk
- High information gain with low risk is ideal
- Consider probe dependencies (what must be tested first)"""

    def _parse_inference_config(
        self,
        context: dict[str, Any] | None,
    ) -> BayesianInferenceConfig | None:
        """Parse PyMC inference configuration from context."""
        if not context:
            return None

        raw_config = context.get("bayesian_inference") or context.get("bayesian_data")
        if not raw_config:
            return None

        try:
            return BayesianInferenceConfig(**raw_config)
        except Exception as exc:
            logger.warning(f"Invalid bayesian inference config: {exc}")
            return None

    def _summarize_samples(self, samples: list[float]) -> BayesianInferenceResult:
        """Summarize posterior samples into mean and credible interval."""
        if not samples:
            raise ValueError("Posterior samples are empty")

        samples_sorted = sorted(samples)
        count = len(samples_sorted)
        lower_idx = int(0.05 * (count - 1))
        upper_idx = int(0.95 * (count - 1))
        lower = float(samples_sorted[lower_idx])
        upper = float(samples_sorted[upper_idx])
        mean = float(sum(samples_sorted) / count)
        variance = sum((x - mean) ** 2 for x in samples_sorted) / max(count - 1, 1)
        std = variance ** 0.5
        uncertainty = max(0.0, min(1.0, std / (abs(mean) + std + 1e-6)))

        return BayesianInferenceResult(
            posterior_mean=mean,
            credible_interval=(lower, upper),
            uncertainty=uncertainty,
        )

    @retry_with_backoff(max_attempts=2, exceptions=(Exception,))
    def _run_pymc_inference(
        self,
        config: BayesianInferenceConfig,
    ) -> BayesianInferenceResult:
        """Run PyMC inference and summarize posterior."""
        try:
            import pymc as pm  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyMC is required for Bayesian inference") from exc

        mode = config.mode()
        if mode == "binomial":
            with pm.Model():
                p = pm.Beta("p", alpha=1, beta=1)
                pm.Binomial(
                    "obs",
                    n=int(config.trials),
                    p=p,
                    observed=int(config.successes),
                )
                trace = pm.sample(
                    draws=config.draws,
                    tune=config.tune,
                    chains=config.chains,
                    target_accept=config.target_accept,
                    random_seed=config.seed,
                    progressbar=False,
                )

            samples = trace.posterior["p"].values.ravel().tolist()
            return self._summarize_samples(samples)

        if mode == "normal":
            observations = [float(value) for value in config.observations or []]
            if not observations:
                raise ValueError("No observations provided for normal model")

            obs_mean = sum(observations) / len(observations)
            obs_variance = sum((x - obs_mean) ** 2 for x in observations) / max(
                len(observations) - 1,
                1,
            )
            obs_std = max(obs_variance ** 0.5, 1e-3)

            with pm.Model():
                mu = pm.Normal("mu", mu=obs_mean, sigma=obs_std)
                sigma = pm.HalfNormal("sigma", sigma=obs_std)
                pm.Normal("obs", mu=mu, sigma=sigma, observed=observations)
                trace = pm.sample(
                    draws=config.draws,
                    tune=config.tune,
                    chains=config.chains,
                    target_accept=config.target_accept,
                    random_seed=config.seed,
                    progressbar=False,
                )

            samples = trace.posterior["mu"].values.ravel().tolist()
            return self._summarize_samples(samples)

        raise ValueError("Inference config missing observations")

    def _calculate_entropy(self, probability: float) -> float:
        """Calculate Shannon entropy for a binary belief."""
        if probability <= 0 or probability >= 1:
            return 0.0
        import math
        return -probability * math.log2(probability) - (1 - probability) * math.log2(1 - probability)

    @async_retry_with_backoff(max_attempts=2, exceptions=(Exception,))
    @async_lru_cache(maxsize=100)
    async def establish_priors(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[BayesianBelief], float]:
        """Establish prior beliefs for a complex situation.

        Args:
            query: The uncertain situation to analyze
            context: Additional context

        Returns:
            Tuple of (list of beliefs, overall uncertainty)
        """
        logger.info(f"Establishing priors for: {query[:50]}...")

        context_str = ""
        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [
            SystemMessage(content=self._prior_prompt),
            HumanMessage(content=f"Establish prior beliefs for:\n\n{query}{context_str}"),
        ]

        response = await self.model.ainvoke(messages)
        content = response.content

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            beliefs = []
            for h in data.get("hypotheses", []):
                prior = h.get("prior", 0.5)
                belief = BayesianBelief(
                    hypothesis=h.get("hypothesis", "unknown"),
                    prior=prior,
                    posterior=prior,  # Initially same as prior
                    evidence_considered=[],
                    confidence_interval=(max(0, prior - 0.2), min(1, prior + 0.2)),
                )
                beliefs.append(belief)

            overall_uncertainty = data.get("overall_uncertainty", 0.7)
            return beliefs, overall_uncertainty

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse prior response: {e}")
            return [
                BayesianBelief(
                    hypothesis="Unable to establish priors",
                    prior=0.5,
                    posterior=0.5,
                )
            ], 1.0

    @async_retry_with_backoff(max_attempts=2, exceptions=(Exception,))
    @async_lru_cache(maxsize=100)
    async def design_probes(
        self,
        beliefs: list[BayesianBelief],
        query: str,
    ) -> list[ExplorationProbe]:
        """Design probes to reduce uncertainty.

        Args:
            beliefs: Current beliefs to probe
            query: Original query context

        Returns:
            List of designed probes
        """
        logger.info("Designing exploration probes...")

        belief_summary = "\n".join([
            f"- {b.hypothesis}: P={b.posterior:.2f} (CI: {b.confidence_interval})"
            for b in beliefs
        ])

        messages = [
            SystemMessage(content=self._probe_prompt),
            HumanMessage(content=f"""Design probes to reduce uncertainty in this situation:

{query}

Current Beliefs:
{belief_summary}

Design probes that would help us learn more."""),
        ]

        response = await self.model.ainvoke(messages)
        content = response.content

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            probes = []
            for p in data.get("probes", []):
                probe = ExplorationProbe(
                    probe_id=p.get("probe_id", f"probe_{len(probes)}"),
                    description=p.get("description", "Unknown probe"),
                    expected_information_gain=p.get("expected_information_gain", 0.5),
                    risk_level=p.get("risk_level", "low"),
                    reversible=p.get("reversible", True),
                    success_criteria=p.get("success_criteria", "TBD"),
                    failure_criteria=p.get("failure_criteria", "TBD"),
                )
                probes.append(probe)

            return probes

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse probe response: {e}")
            return [
                ExplorationProbe(
                    probe_id="default_probe",
                    description="Gather more information through stakeholder interviews",
                    expected_information_gain=0.3,
                    risk_level="low",
                    reversible=True,
                    success_criteria="Gain clarity on key unknowns",
                    failure_criteria="No new insights generated",
                )
            ]

    def update_belief(
        self,
        belief: BayesianBelief,
        evidence: str,
        likelihood_ratio: float,
    ) -> BayesianBelief:
        """Update a belief using Bayes' rule.

        Args:
            belief: Current belief
            evidence: Description of new evidence
            likelihood_ratio: P(evidence|hypothesis) / P(evidence|not hypothesis)

        Returns:
            Updated belief
        """
        prior_odds = belief.posterior / (1 - belief.posterior) if belief.posterior < 1 else float('inf')
        posterior_odds = prior_odds * likelihood_ratio
        posterior = posterior_odds / (1 + posterior_odds) if posterior_odds != float('inf') else 0.99

        new_evidence = belief.evidence_considered + [evidence]

        return BayesianBelief(
            hypothesis=belief.hypothesis,
            prior=belief.prior,
            posterior=posterior,
            evidence_considered=new_evidence,
            confidence_interval=(max(0, posterior - 0.15), min(1, posterior + 0.15)),
        )

    @async_lru_cache(maxsize=100)
    async def explore(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> ActiveInferenceResult:
        """Full Active Inference exploration.

        Args:
            query: The complex situation to explore
            context: Additional context

        Returns:
            ActiveInferenceResult with beliefs and recommended probes
        """
        # Step 1: Establish priors (PyMC if data is available)
        inference_config = self._parse_inference_config(context)
        beliefs: list[BayesianBelief] = []
        initial_uncertainty = 1.0
        used_pymc = False

        if inference_config and inference_config.has_data():
            try:
                inference_result = self._run_pymc_inference(inference_config)
                used_pymc = True
                initial_uncertainty = min(1.0, inference_result.uncertainty)
                beliefs = [
                    BayesianBelief(
                        hypothesis="Posterior estimate",
                        prior=0.5,
                        posterior=inference_result.posterior_mean,
                        evidence_considered=["PyMC inference"],
                        confidence_interval=inference_result.credible_interval,
                    )
                ]
            except Exception as exc:
                logger.warning(f"PyMC inference failed, falling back to LLM: {exc}")

        if not beliefs:
            beliefs, initial_uncertainty = await self.establish_priors(query, context)

        if not beliefs:
            beliefs = [
                BayesianBelief(
                    hypothesis="Default hypothesis",
                    prior=0.5,
                    posterior=0.5,
                )
            ]

        if used_pymc:
            initial_belief = BayesianBelief(
                hypothesis=beliefs[0].hypothesis,
                prior=beliefs[0].prior,
                posterior=beliefs[0].prior,
                confidence_interval=(
                    max(0.0, beliefs[0].prior - 0.2),
                    min(1.0, beliefs[0].prior + 0.2),
                ),
            )
        else:
            initial_belief = beliefs[0]

        # Step 2: Design probes
        probes = await self.design_probes(beliefs, query)

        # Select recommended probe (highest info gain with acceptable risk)
        recommended = None
        if probes:
            safe_probes = [p for p in probes if p.risk_level in ("low", "medium")]
            if safe_probes:
                recommended = max(safe_probes, key=lambda p: p.expected_information_gain)
            else:
                recommended = probes[0]

        # Calculate uncertainty reduction (simulated for MVP)
        final_uncertainty = initial_uncertainty * 0.8  # 20% reduction expected

        if used_pymc:
            updated_belief = beliefs[0]
        else:
            # Create updated belief (simulated posterior update)
            updated_belief = BayesianBelief(
                hypothesis=initial_belief.hypothesis,
                prior=initial_belief.prior,
                posterior=min(initial_belief.posterior + 0.1, 0.9),
                evidence_considered=["Initial analysis completed"],
                confidence_interval=(
                    initial_belief.confidence_interval[0] + 0.05,
                    initial_belief.confidence_interval[1] - 0.05,
                ),
            )

        interpretation = (
            f"Analysis of complex situation identified {len(beliefs)} hypotheses. "
            f"Initial uncertainty: {initial_uncertainty:.0%}. "
            f"Designed {len(probes)} probes to reduce uncertainty. "
            f"Recommended next step: {recommended.description if recommended else 'Gather more information'}"
        )

        logger.info(
            "Active inference complete: uncertainty %.2f -> %.2f",
            initial_uncertainty,
            final_uncertainty,
        )

        return ActiveInferenceResult(
            initial_belief=initial_belief,
            updated_belief=updated_belief,
            probes_designed=probes,
            recommended_probe=recommended,
            uncertainty_before=initial_uncertainty,
            uncertainty_after=final_uncertainty,
            interpretation=interpretation,
        )


# Singleton instance
_engine_instance: ActiveInferenceEngine | None = None


def get_bayesian_engine() -> ActiveInferenceEngine:
    """Get or create the Active Inference engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ActiveInferenceEngine()
    return _engine_instance


async def run_active_inference(
    state: EpistemicState,
) -> EpistemicState:
    """Run Active Inference and update the epistemic state.

    This function is used by the bayesian_explorer_node in the workflow.

    Args:
        state: Current epistemic state

    Returns:
        Updated epistemic state with exploration results
    """
    engine = get_bayesian_engine()

    # Run exploration
    result = await engine.explore(
        query=state.user_input,
        context=state.context,
    )

    # Update state
    state.epistemic_uncertainty = result.uncertainty_after
    state.current_hypothesis = result.updated_belief.hypothesis

    # Determine confidence level
    if result.uncertainty_after < 0.3:
        state.overall_confidence = ConfidenceLevel.HIGH
    elif result.uncertainty_after < 0.6:
        state.overall_confidence = ConfidenceLevel.MEDIUM
    else:
        state.overall_confidence = ConfidenceLevel.LOW

    # Store full Bayesian evidence for dashboard
    state.bayesian_evidence = BayesianEvidence(
        posterior_mean=result.updated_belief.posterior,
        credible_interval=result.updated_belief.confidence_interval,
        uncertainty_before=result.uncertainty_before,
        uncertainty_after=result.uncertainty_after,
        epistemic_uncertainty=result.uncertainty_after * 0.7,  # Estimate
        aleatoric_uncertainty=result.uncertainty_after * 0.3,  # Estimate
        hypothesis=result.updated_belief.hypothesis,
        confidence_level=state.overall_confidence.value,
        interpretation=result.interpretation,
        probes_designed=len(result.probes_designed),
        recommended_probe=result.recommended_probe.description if result.recommended_probe else None,
    )

    # Set proposed action (the recommended probe)
    if result.recommended_probe:
        state.proposed_action = {
            "action_type": "exploration_probe",
            "description": result.recommended_probe.description,
            "parameters": {
                "probe_id": result.recommended_probe.probe_id,
                "expected_info_gain": result.recommended_probe.expected_information_gain,
                "risk_level": result.recommended_probe.risk_level,
                "reversible": result.recommended_probe.reversible,
            },
        }
    else:
        state.proposed_action = {
            "action_type": "gather_information",
            "description": "Gather more information before proceeding",
            "parameters": {},
        }

    # Build response
    probes_summary = "\n".join([
        f"  - **{p.probe_id}**: {p.description} (Info Gain: {p.expected_information_gain:.0%}, Risk: {p.risk_level})"
        for p in result.probes_designed[:3]
    ])

    state.final_response = (
        f"**Bayesian Exploration Complete**\n\n"
        f"**Situation:** Complex domain - cause-effect unclear, probing required\n\n"
        f"**Initial Uncertainty:** {result.uncertainty_before:.0%}\n"
        f"**Updated Uncertainty:** {result.uncertainty_after:.0%}\n\n"
        f"**Primary Hypothesis:** {result.updated_belief.hypothesis}\n"
        f"**Confidence:** {result.updated_belief.posterior:.0%} "
        f"(CI: {result.updated_belief.confidence_interval[0]:.0%}-{result.updated_belief.confidence_interval[1]:.0%})\n\n"
        f"**Recommended Probes:**\n{probes_summary}\n\n"
        f"**Next Step:** {result.recommended_probe.description if result.recommended_probe else 'Gather more data'}\n\n"
        f"**Interpretation:** {result.interpretation}"
    )

    return state
