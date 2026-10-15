"""Dossiê executivo local, sempre com limites e estado real."""

from .contracts import RunResult


def executive_markdown(result: RunResult) -> str:
    lines = [
        "# Dossiê investigativo — agente_insider",
        "",
        f"Execução: `{result.run_id}`  ",
        f"Snapshot: `{result.snapshot_id}`  ",
        f"Estado: **{result.status}** · backend: **{result.backend_mode}**",
        "",
        "**Revisão humana obrigatória. Hipóteses sem comprovação empírica.**",
        "Nenhuma redução de falsos positivos comprovada; regras oficiais preservadas.",
        "",
    ]
    if result.backend_mode == "TEST_FIXTURE":
        lines += [
            "**TESTE SINTÉTICO: este documento não contém achados reais nem execução de LLM.**",
            "",
        ]
    if result.error_code:
        lines += [
            f"Execução bloqueada: `{result.error_code}`. Etapas dependentes não executadas.",
            "",
        ]
    lines += ["| Etapa | Estado | Tentativas | Tempo (ms) |", "|---|---|---:|---:|"]
    lines += [
        f"| {m.stage} | {m.status} | {m.attempts} | {m.elapsed_ms:.1f} |" for m in result.metrics
    ]
    executive = result.stages.get("executive_intelligence")
    if executive and result.status == "COMPLETE_STRUCTURALLY_VALIDATED":
        lines += ["", "## Síntese proposta pelo modelo", "", executive["summary"]]
        for key, label in [
            ("limitations", "Limitações"),
            ("risks", "Riscos"),
            ("recommended_tests", "Testes propostos"),
            ("technical_dependencies", "Dependências"),
            ("human_decisions", "Decisões humanas"),
            ("next_steps", "Próximos passos"),
        ]:
            lines += ["", f"## {label}", ""] + [f"- {item}" for item in executive[key]]
    return "\n".join(lines) + "\n"
