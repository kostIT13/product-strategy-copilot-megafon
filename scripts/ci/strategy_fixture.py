"""Authored synthetic documents for mechanical CI tests, never market evidence."""


def synthetic_strategies(capability_id="CAP-001"):
    return {
        "product-strategy.md": f"""# Synthetic product strategy

## Аудитория и задача

[HYPOTHESIS] Test operators need a local fixture to check whether a file workflow can be resumed safely.

## Ценность и альтернативы

Synthetic CSV export is available in the generated fixture only [COMMITMENT: {capability_id}]. [HYPOTHESIS] Manual handling is an alternative to compare before a real decision.

## Выбор и осознанные отказы

[HYPOTHESIS] Choose only a synthetic trial and decline automatic public rollout until a human compares alternatives.

## Связь пользы с затратами и доходами

[OPEN QUESTION] Costs and revenue have not been measured; the fixture actor must obtain them before a real rollout.
""",
        "communication-strategy.md": """# Synthetic communication strategy

## Аудитория и ситуация

[HYPOTHESIS] The audience is the fixture test operator checking a local export in a controlled test situation.

## Барьер понимания или выбора

[HYPOTHESIS] The operator may confuse synthetic fixture capability with a verified product outcome and needs a clear limit.

## Ключевое сообщение и подтверждение

[HYPOTHESIS] A message about export can be tested after a human checks its meaning and conditions against actual evidence.

## Роль каналов

[HYPOTHESIS] Use a local test note for understanding and feedback; public promotion is outside this synthetic trial.
""",
    }
