"""Stable task identifiers persisted with requests and pipeline checkpoints."""
from typing import Literal

AnalysisTask = Literal["evidence_answer", "evidence_extraction", "strategy_options"]
AgentTask = Literal["evidence_answer", "evidence_extraction", "strategy_options", "evidence_critic"]
# Fresh-retrieval tasks only. Critic requires a saved input run via its own service.
TASK_NAMES = ("evidence_answer", "evidence_extraction", "strategy_options")
