"""LLM-as-a-judge: criteria, providers, cached verdicts and judge calibration."""

from guage_kit.judges.calibration import agreement, position_consistency, weighted_kappa
from guage_kit.judges.criteria import CRITERIA, Criterion, get_criterion
from guage_kit.judges.judge import (
    BaseJudge,
    HeuristicJudge,
    LLMJudge,
    PairwiseVerdict,
    Verdict,
    make_judge,
)
from guage_kit.judges.providers import (
    AnthropicProvider,
    CallableProvider,
    Completion,
    OpenAICompatibleProvider,
    Provider,
    make_provider,
)

__all__ = [
    "CRITERIA",
    "AnthropicProvider",
    "BaseJudge",
    "CallableProvider",
    "Completion",
    "Criterion",
    "HeuristicJudge",
    "LLMJudge",
    "OpenAICompatibleProvider",
    "PairwiseVerdict",
    "Provider",
    "Verdict",
    "agreement",
    "get_criterion",
    "make_judge",
    "make_provider",
    "position_consistency",
    "weighted_kappa",
]
