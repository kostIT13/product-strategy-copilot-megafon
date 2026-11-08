"""Stable task identifiers persisted with requests and pipeline checkpoints."""
from typing import Literal

AgentTask = Literal["evidence_answer", "evidence_extraction"]
TASK_NAMES = ("evidence_answer", "evidence_extraction")
