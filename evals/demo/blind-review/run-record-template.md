# Run record — MVP M6

Copy this file for each paired A/B run. Keep the owner key separate from the evaluator until scoring is complete. Do not fill unknown measurements with zero.

## Pair and conditions

- Pair ID:
- Date and timezone:
- Case/input revision and SHA-256:
- Exact model/provider/version for both conditions:
- Model settings (reasoning level, temperature if available, other limits):
- Equal wall-clock limit per condition:
- Equal output/token limit, if available:
- Condition order and how order was chosen:
- Human operator and prior familiarity with the workflow:
- Deviations from protocol:

## Condition A — baseline

- Prompt revision/hash:
- Start / stop timestamps:
- Model elapsed time (provider-reported; otherwise unknown):
- Human elapsed time:
- Input/output tokens (measured or unknown):
- API cost, currency, certainty, pricing date/source (unknown if unavailable):
- Retries, errors, interruptions, human assistance:
- Output artifact path/hash:

## Condition B — CLI workflow

- Workflow/code commit:
- Start / stop timestamps:
- Model elapsed time (provider-reported; otherwise unknown):
- Human elapsed time:
- Input/output tokens (measured or unknown):
- API cost, currency, certainty, pricing date/source (unknown if unavailable):
- Retries, errors, interruptions, human assistance:
- Output artifact path/hash:
- `validate` result:
- `verify` result:

## Independent scoring

- Evaluator (name or stable pseudonym):
- Evaluator received only neutral A/B packets: yes/no; explain deviations:
- Scores and evidence: complete the rubric in `reviewer-brief.md` without consulting `owner-key.md`.
- Evaluator's guess about which packet used which method, recorded after scoring:
- Evaluator confidence and clues:
- Strongest recommendation-changing fact/test:
- Evaluator time spent:
- Evaluator costs (or unknown):

## Result and limits

- Score A / 14:
- Score B / 14:
- Difference:
- Technical validation results (report separately from quality scores):
- What this single case does not establish:
- Owner review date:

M6 remains open until the pair meets the equal-condition protocol and an independent evaluator has completed the rubric. One case is a pilot observation, not statistical evidence.
