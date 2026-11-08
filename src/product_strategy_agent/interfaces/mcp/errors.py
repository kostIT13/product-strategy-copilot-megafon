"""Return safe domain errors without exposing backend exception details."""
from fastmcp.exceptions import ToolError

from product_strategy_agent.domain.agent.models import AgentRunFailed
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def invoke(operation):
    try:
        return operation()
    except (AgentRunFailed, ProjectNotFound, ValueError) as exc:
        raise ToolError(str(exc)) from None
    except Exception:
        raise ToolError("main service operation failed; check local service configuration") from None
