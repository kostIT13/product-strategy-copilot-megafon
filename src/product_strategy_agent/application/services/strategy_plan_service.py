"""Read-only planning preview and explicit checkpoint creation for a selected decision."""


class StrategyPlanService:
    def __init__(self, context, pipeline):
        self.context, self.pipeline = context, pipeline

    def prepare(self, project_key, source_run_id, question):
        return self.context.create(project_key, source_run_id, question)

    def start(self, project_key, source_run_id, question):
        prepared = self.prepare(project_key, source_run_id, question)
        self.context.inputs.put(prepared.project_id, prepared.input_hash, prepared.review_target)
        return self.pipeline.start_prepared(prepared)
