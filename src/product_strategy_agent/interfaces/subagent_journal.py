"""Composition root shared by CLI/MCP; journal behaviour stays in application services."""

from product_strategy_agent.adapters.persistence.files.handoff_reader import (
    FileHandoffReader,
)
from product_strategy_agent.adapters.persistence.files.role_instruction_reader import (
    FileRoleInstructionReader,
)
from product_strategy_agent.adapters.persistence.files.task_journal_store import (
    FileTaskJournalStore,
)
from product_strategy_agent.application.services.handoff_service import HandoffService
from product_strategy_agent.application.services.task_journal_service import (
    TaskJournalService,
)


def journal_service(projects_dir, instructions_root):
    return TaskJournalService(
        FileTaskJournalStore(projects_dir),
        HandoffService(
            FileHandoffReader(projects_dir),
            FileRoleInstructionReader(instructions_root),
        ),
    )
