"""Explicit offline construction of an entirely synthetic, unapproved case."""

import argparse
import json
from pathlib import Path
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.domain.projects.workspace import current_workspace_seed
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.ledger import add_claim, add_gap, add_option, add_capability
from product_strategy_agent.rendering import render_project

ASSETS = Path(__file__).resolve().parent


def require_empty_seed(case, project_id, root):
    state = load_state(project_id, root)
    seed = current_workspace_seed(project_id, state["created_at"])
    for name, expected in seed.files.items():
        if (case / name).read_text(encoding="utf-8") != expected:
            raise ValueError(
                "existing case is not an untouched current init seed; no overwrite"
            )
    for path in case.rglob("*"):
        name = path.relative_to(case).as_posix()
        if path.is_file() and name not in seed.files and not name.startswith(".psa/"):
            raise ValueError("existing case contains additional files; no overwrite")


def anchor(claim, source, locator, quote, value, unit):
    start, unit_start = quote.index(value), quote.index(unit)
    return {
        "schema_version": 1,
        "claim_id": claim["claim_id"],
        "source_id": source["source_id"],
        "locator": locator,
        "quote": quote,
        "number_span": {"start": start, "end": start + len(value)},
        "unit_span": {"start": unit_start, "end": unit_start + len(unit)},
    }


def measurement(operands):
    plan = {
        "schema_version": 1,
        "hypothesis": "Синтетическая гипотеза: самостоятельный перенос сохраняет посещения без роста ошибок мест и поддержки.",
        "expected_change": "Предложение к обсуждению: уменьшение неиспользованных записей; эффект не наблюдался и не обещан.",
        "metric": {
            "name": "Доля неиспользованных записей",
            "definition": "Число записей без посещения или своевременного переноса / все eligible записи в заранее зафиксированной когорте; отмены и исключения описать до анализа.",
            "unit": "%",
            "population": "Будущая согласованная когорта студии; учебная таблица не репрезентативна и не задаёт реальный baseline.",
            "data_source": "Будущий согласованный журнал бронирований/посещений/переносов; сейчас только synthetic operations.txt.",
        },
        "baseline": {
            "status": "unknown",
            "value": None,
            "reason": "20% вычисляется лишь в вымышленном файле; реального baseline и причин пропусков нет.",
            "measurement": {
                "method": "До запуска проверить определения/полноту и измерить сопоставимую когорту; не переносить учебные проценты на реальных людей.",
                "owner": "Предлагаемая учебная роль: аналитик студии; реальный человек не назначен.",
                "due_at": "2026-12-01T18:00:00+07:00",
            },
        },
        "comparison": "Предложение: self-service против текущей ручной помощи; правила включения/назначения и анализ согласовать заранее. Историческую synthetic таблицу не считать контрольной группой.",
        "success_criterion": "Порог практической значимости, достаточность наблюдений и правило анализа согласовать до запуска; пока они неизвестны, не запускать и не объявлять успех.",
        "observation": {
            "start_condition": "Только после выбора человека, проверки реализации, baseline, бюджета и согласованного протокола; учебное предложение окна, не срок обязательства.",
            "duration_days": 28,
        },
        "guardrails": [
            {
                "name": "Конфликт мест",
                "definition": "Подтверждённый перенос в занятое место или потеря исходной записи.",
                "data_source": "Будущие журнал транзакций и ручной разбор.",
                "stop_rule": "При любом подтверждённом конфликте остановить сценарий и сохранить ручное обслуживание.",
                "owner": "Учебная роль: операционный владелец, не назначен.",
            },
            {
                "name": "Неожиданный платёж",
                "definition": "Новое списание/изменение цены при заявленном переносе той же цены.",
                "data_source": "Будущий audit платежных событий; платежи вне scope.",
                "stop_rule": "Любое подтверждённое событие требует немедленной остановки и разбора.",
                "owner": "Учебная роль: операционный владелец, не назначен.",
            },
            {
                "name": "Нагрузка и непонимание",
                "definition": "Время поддержки и ошибочное ожидание возврата/свободного места.",
                "data_source": "Будущий обезличенный учёт обращений при разрешённом сборе.",
                "stop_rule": "Сравнить с согласованным baseline; предел вреда определить до запуска, без него тест не начинать.",
                "owner": "Учебная роль: руководитель студии, не назначен.",
            },
        ],
        "owner": "Сценарная роль: руководитель студии; реальное согласование отсутствует.",
        "decision_rule": "Без валидного дизайна/данных и human choice — доработать постановку. При вреде — остановить; при недостатке данных — не считать гипотезу подтверждённой. Масштабирование выбирает человек отдельно.",
    }
    calculations = {
        "schema_version": 1,
        "calculations": [
            {
                "calculation_id": "CALC-001",
                "operation": "percentage",
                "period_relation": "same",
                "operands": operands,
                "expected_value": "20",
                "result_unit": "%",
            },
            {
                "calculation_id": "CALC-002",
                "operation": "ratio",
                "period_relation": "same",
                "operands": operands,
                "expected_value": "0.2",
                "result_unit": "ratio",
            },
        ],
    }
    return (
        "# Условный план проверки «Слот»\n\nПолностью синтетический сценарий; выбор, бюджет и эксперимент не разрешены. Даты/окно — учебные предложения, реальные ответственные не назначены.\n\n"
        "Учебный расчёт 40 / 200 = 0.2 = 20% относится только к созданному файлу. Он не является результатом пилота, прогнозом эффекта или реальным baseline. Реальный baseline unknown; порог/размер выборки неизвестны.\n\n"
        + "```psa-validation-v1\n"
        + json.dumps(plan, ensure_ascii=False, indent=2)
        + "\n```\n\n"
        + "```psa-calculations-v1\n"
        + json.dumps(calculations, ensure_ascii=False, indent=2)
        + "\n```\n"
    )


def populate(case, project_id, root):
    with case_access(root, project_id):
        require_empty_seed(case, project_id, root)
        materials = {}
        for name in ("operations", "capabilities", "constraints"):
            materials[name] = add_local_source(
                case, ASSETS / "materials" / (name + ".txt"), title="SYNTHETIC: " + name
            )
        quotes = [
            (
                "operations",
                2,
                "Synthetic scheduled total is 200 bookings.",
                "fact",
                "Учебный файл содержит вымышленный знаменатель 200 bookings; не факт о реальном бизнесе.",
            ),
            (
                "operations",
                3,
                "Synthetic unused total is 40 bookings.",
                "fact",
                "Учебный файл содержит вымышленный числитель 40 bookings; не наблюдение клиентов.",
            ),
            (
                "operations",
                4,
                "Synthetic unused rate is 20 %.",
                "fact",
                "В учебном файле записано 20%; это проверяемое содержание файла, не реальный baseline.",
            ),
            (
                "constraints",
                2,
                "The intended job is to preserve a usable booking when plans change, while avoiding duplicate seats and unexpected charges. The user is the attendee; the buyer and operational owner would be the studio manager.",
                "synthetic",
                "Вымышленная задача/роли: сохранить занятие при изменении планов; спрос не исследован.",
            ),
            (
                "capabilities",
                2,
                "The fictional studio currently offers a schedule page and administrator-assisted changes. A self-service rescheduling flow is planned, not available.",
                "synthetic",
                "Сценарный self-service planned; реальной реализации нет.",
            ),
            (
                "capabilities",
                4,
                "Automatic refunds, price changes, payments and a marketplace across studios are outside the proposed scope and unavailable in the scenario.",
                "synthetic",
                "В сценарии исключены возвраты/изменения цены/платежи/маркетплейс.",
            ),
        ]
        claims = []
        for material, paragraph, quote, kind, text in quotes:
            # Read the registered extraction before recording its exact citation.
            source = materials[material]
            extracted = (case / source["extracted_text_path"]).read_text(
                encoding="utf-8"
            )
            if quote not in extracted:
                raise ValueError("synthetic source quote unavailable")
            claims.append(
                add_claim(
                    case,
                    text,
                    kind,
                    [source["source_id"]],
                    [f"paragraph:{paragraph}"],
                    [quote],
                    reasoning_note="Один автор, полностью synthetic. Fact описывает артефакт, не реальный рынок.",
                )
            )
        add_claim(
            case,
            "Самостоятельный перенос может быть полезен при наличии подходящего места; пока гипотеза.",
            "hypothesis",
            reasoning_note="Не подкреплена реальными интервью/экспериментом.",
        )
        for question, why, method in (
            (
                "Почему посетители не приходят и есть ли подходящие свободные слоты?",
                "Self-service может решать не ту проблему.",
                "При отдельном разрешении исследовать причины и inventory; синтетика не заменяет наблюдение.",
            ),
            (
                "Каковы реальный baseline, стоимость поддержки и маржинальный эффект?",
                "Без них нельзя выбрать бюджет или обещать ROI.",
                "Согласовать определения/когорту/учёт затрат до запуска.",
            ),
            (
                "Каковы порог полезности, объём наблюдений и предел допустимого вреда?",
                "Без заранее согласованного правила нельзя объявить успех.",
                "Согласовать протокол с человеком и аналитиком, не подгонять пороги к исходу.",
            ),
        ):
            add_gap(case, question, why, method, "high")
        options = (
            (
                "Ручной перенос",
                "status_quo",
                "Оставить администратора и сделать правила понятнее.",
                "Обратимость и помощь при исключениях.",
                "Ручное время, реальная величина неизвестна.",
                "Зависимость от часов поддержки.",
                "Может не устранять неудобство посетителя.",
                "Ручной процесс достаточно доступен.",
            ),
            (
                "Закрыть self-service направление",
                "stop",
                "Не строить отдельный интерфейс, исследовать расписание и вместимость.",
                "Не тратить ресурсы на неподтверждённую потребность.",
                "Упущенная возможность обучения; величина неизвестна.",
                "Проблема изменения планов может сохраниться.",
                "Ранний отказ способен пропустить полезный узкий сценарий.",
                "Причина пропусков преимущественно в расписании.",
            ),
            (
                "Узкий перенос без платежей",
                "change",
                "Предложить ограниченный обратимый пилот, только после выбора и проверок.",
                "Гипотеза меньших усилий и сохранённых посещений.",
                "Неизвестные разработка/поддержка/вытеснение продаж.",
                "Конфликт мест, непонимание цены и отсутствие подходящего слота.",
                "Автоматизация может не создать дополнительной пользы.",
                "Есть достаточное предложение подходящих свободных мест.",
            ),
        )
        for (
            name,
            role,
            description,
            benefit,
            costs,
            risks,
            objection,
            assumption,
        ) in options:
            add_option(
                case,
                name,
                role,
                description,
                benefit,
                costs,
                risks,
                objection,
                [assumption],
                [claims[0]["claim_id"], claims[1]["claim_id"], claims[3]["claim_id"]],
            )
        add_capability(
            case,
            "Учебный самостоятельный перенос: реальной реализации нет",
            "planned",
            [claims[4]["claim_id"]],
        )
        add_capability(
            case,
            "Автоматические возвраты/изменение цены в сценарии",
            "unavailable",
            [claims[5]["claim_id"]],
        )
        (case / "01_brief.md").write_text(
            (ASSETS / "brief.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        (case / "02_research-plan.md").write_text(
            (ASSETS / "research-plan.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        render_project(case)
        for name in ("product-strategy", "communication-strategy"):
            (case / "drafts" / (name + ".md")).write_text(
                (ASSETS / (name + ".md")).read_text(encoding="utf-8"), encoding="utf-8"
            )
        context = {
            "metric": "Unused bookings in synthetic file",
            "population": "Fictional studio bookings only",
            "period": "2026-10 synthetic",
            "conditions": "Same fictional file/definition; no real observations",
        }
        operands = {}
        for name, index, value in (("numerator", 1, "40"), ("denominator", 0, "200")):
            source = materials["operations"]
            operands[name] = {
                "anchor": anchor(
                    claims[index],
                    source,
                    f"paragraph:{index + 2}",
                    quotes[index][2],
                    value,
                    "bookings",
                ),
                "context": dict(context),
            }
        (case / "drafts/validation-plan.md").write_text(
            measurement(operands), encoding="utf-8"
        )
        analysis = case / "analysis"
        analysis.mkdir(exist_ok=True)
        (analysis / "methods-used.md").write_text(
            (ASSETS / "methods-used.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        (analysis / "options-comparison.md").write_text(
            (ASSETS / "options-comparison.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        render_project(case)
        return {
            "project_id": project_id,
            "status": load_state(project_id, root)["status"],
            "synthetic": True,
            "human_decision_recorded": False,
            "approvals_granted": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default="slot-workshop-synthetic")
    parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
    parser.add_argument("--use-empty-initialized", action="store_true")
    args = parser.parse_args()
    case = args.projects_dir.resolve() / args.project_id
    if not args.use_empty_initialized:
        case = init_project(args.project_id, args.projects_dir)
    print(
        json.dumps(
            populate(case, args.project_id, args.projects_dir), ensure_ascii=True
        )
    )


if __name__ == "__main__":
    main()
