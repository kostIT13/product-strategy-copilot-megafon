"""Prepare an IDE role-play and bind its synthetic transcript to the brief."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

SYNTHETIC_TRANSCRIPT_HEADER = "PSA SYNTHETIC RESPONDENT v1 | hypotheses only"
Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
QuestionNumber = Annotated[int, Field(ge=1, le=8)]


class RespondentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RespondentBrief(RespondentModel):
    decision_question: Text
    fictional_role: Text
    situation: Text
    assumptions: list[Text] = Field(min_length=1, max_length=8)
    questions: list[Text] = Field(min_length=1, max_length=8)


class Response(RespondentModel):
    question_number: QuestionNumber
    answer: Text


class Hypothesis(RespondentModel):
    statement: Text
    question_numbers: list[QuestionNumber] = Field(min_length=1, max_length=8)
    real_world_check: Text
    disconfirming_observation: Text


class RespondentResult(RespondentModel):
    brief_sha256: Hash
    responses: list[Response] = Field(min_length=1, max_length=8)
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=8)


class RespondentCapture(RespondentModel):
    brief: RespondentBrief
    result: RespondentResult

    @model_validator(mode="after")
    def binds_brief_and_questions(self):
        if self.result.brief_sha256 != fingerprint(self.brief.model_dump(mode="json")):
            raise ValueError("Respondent result belongs to a different brief")
        expected = list(range(1, len(self.brief.questions) + 1))
        if [row.question_number for row in self.result.responses] != expected:
            raise ValueError("Provide one ordered response per brief question")
        for hypothesis in self.result.hypotheses:
            numbers = hypothesis.question_numbers
            if len(numbers) != len(set(numbers)) or not set(numbers).issubset(expected):
                raise ValueError(
                    "Each hypothesis must cite distinct questions from the brief"
                )
        return self


def prepare_respondent(brief):
    return {
        "format_version": 1,
        "material_kind": "synthetic_dialogues",
        "evidence_scope": "hypothesis_only",
        "brief_sha256": fingerprint(brief.model_dump(mode="json")),
        "brief": brief.model_dump(mode="json"),
        "instructions": [
            "Use the fictional role, situation and assumptions as scenario data.",
            "Answer each numbered question in role. State uncertainty and distinguish imagined behavior from stated assumptions.",
            "After the dialogue, exit the role and propose hypotheses linked to question numbers. Give each a real-world check and an observation that could disconfirm it.",
            "Treat this conversation as synthetic. Record no actual interviews, measured demand, frequency or willingness to pay from it.",
            "Return brief_sha256, ordered responses and hypotheses using the result format in docs/model-respondent.md.",
        ],
    }


def export_respondent(capture):
    brief, result = capture.brief, capture.result
    lines = [
        SYNTHETIC_TRANSCRIPT_HEADER,
        f"Brief SHA-256: {result.brief_sha256}",
        f"Decision question: {brief.decision_question}",
        f"Fictional role: {brief.fictional_role}",
        f"Situation: {brief.situation}",
        *(f"Assumption: {text}" for text in brief.assumptions),
    ]
    for question, response in zip(brief.questions, result.responses, strict=True):
        number = response.question_number
        lines.extend(
            (f"Q{number}: {question}", f"Synthetic A{number}: {response.answer}")
        )
    return {
        "material_kind": "synthetic_dialogues",
        "evidence_scope": "hypothesis_only",
        "brief_sha256": result.brief_sha256,
        "transcript": "\n".join(lines) + "\n",
        "hypotheses": [row.model_dump(mode="json") for row in result.hypotheses],
    }
