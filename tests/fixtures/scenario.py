"""Cenário fabricado: não reproduz contagens ou resultados históricos reais."""

import json
from types import SimpleNamespace

import pandas as pd

from agente_insider.config import AdapterConfig
from agente_insider.data.evidence_builder import build_snapshot
from agente_insider.governance.security import model_payload
from agente_insider.llm.base import ModelReply


def frames():
    # Mesmo padrão repetido em duas bases fabricadas, sem nomes ou clientes.
    return {
        scope: pd.DataFrame(
            {
                "z_score_20dias_d0": [2.0] * count,
                "z_score_20dias_d1": [1.0] * count,
                "delta_z": [1.0] * count,
            }
        )
        for scope, count in [("PF", 10), ("PJ", 15)]
    }


def runreport():
    return SimpleNamespace(results={s: SimpleNamespace(cases=f) for s, f in frames().items()})


def snapshot():
    return build_snapshot(
        frames=frames(),
        source_references={"PF": "TEST_FIXTURE:PF", "PJ": "TEST_FIXTURE:PJ"},
        source_run_id="TEST-ONLY-001",
        origin="TEST_FIXTURE",
        config=AdapterConfig(),
        complete_extract={"PF": True, "PJ": True},
    )


def outputs(snap=None):
    snap = snap or snapshot()
    payload = model_payload(snap)
    pattern = payload["patterns"][0]
    evidence_id = pattern["evidence_ids"][0]
    refs = [evidence_id]
    hypothesis_id = "H-TEST-1"
    return {
        "hypothesis_generator": {
            "hypotheses": [
                {
                    "hypothesis_id": hypothesis_id,
                    "title": "Hipótese fabricada para teste",
                    "statement": "Uma transformação comum poderia explicar indicadores repetidos.",
                    "originating_pattern_ids": [pattern["pattern_id"]],
                    "supporting_evidence_ids": refs,
                    "alternative_explanations": [
                        "Eventos independentes poderiam produzir o padrão."
                    ],
                    "missing_data": ["Linhagem e desfechos adjudicados não foram fornecidos."],
                    "proposed_tests": [
                        {
                            "name": "Teste futuro de linhagem",
                            "required_data": ["Linhagem aprovada e rodadas posteriores"],
                            "method": "Comparar em recorte temporal independente.",
                            "falsification_criteria": "Ausência da transformação sugerida.",
                            "temporal_holdout_required": True,
                        }
                    ],
                    "falsification_criteria": ["A causa proposta não aparece na linhagem."],
                    "limitations": ["Cenário de teste sintético; hipótese sem validação."],
                    "empirical_status": "UNTESTED",
                }
            ]
        },
        "evidence_investigator": {
            "investigations": [
                {
                    "hypothesis_id": hypothesis_id,
                    "findings": [
                        {
                            "evidence_id": evidence_id,
                            "interpretation": "Contagem agregada.",
                            "category": "OBSERVED",
                        }
                    ],
                    "missing_information": ["Desfechos históricos indisponíveis."],
                    "pending_tests": ["Validar a linhagem com especialistas."],
                    "proposed_tool": "REQUEST_APPROVED_HISTORY",
                }
            ]
        },
        "critical_reviewer": {
            "reviews": [
                {
                    "hypothesis_id": hypothesis_id,
                    "evidence_ids": refs,
                    "alternative_explanations": ["Coincidência na transformação de indicadores."],
                    "confounders": ["Viés de seleção de alertas."],
                    "extrapolations": ["Não generalizar este recorte."],
                    "counterevidence": [],
                    "refutation_tests": ["Inspecionar linhagem em outro período."],
                    "interpretation_risks": ["Correlação não comprova causa."],
                }
            ]
        },
        "methodological_validator": {
            "validations": [
                {
                    "hypothesis_id": hypothesis_id,
                    "evidence_ids": refs,
                    "status": "NEEDS_DATA",
                    "reproducibility_gaps": ["Falta linhagem aprovada."],
                    "selection_bias": "Apenas alertas foram selecionados.",
                    "leakage_risk": "Separar dados de desenvolvimento e teste.",
                    "temporal_validation": "Reservar rodadas posteriores.",
                    "statistical_limitations": ["Sem histórico rotulado."],
                    "correlation_is_not_causation": True,
                    "historical_outcomes_available": False,
                    "empirically_validated": False,
                }
            ]
        },
        "risk_specialist": {
            "risks": [
                {
                    "hypothesis_id": hypothesis_id,
                    "evidence_ids": refs,
                    "false_negative_risk": "UNKNOWN",
                    "safeguards": ["Preservar o monitoramento e revisão humana."],
                    "minimum_experiment_conditions": ["Rodar em sombra com dados autorizados."],
                    "human_decisions_required": ["Aprovar o desenho experimental."],
                    "recommended_action": "HUMAN_REVIEW_ONLY",
                    "auto_suppression_allowed": False,
                    "official_rule_change_allowed": False,
                }
            ]
        },
        "executive_intelligence": {
            "summary": "Teste sintético do fluxo; nenhuma hipótese comprovada.",
            "observed_pattern_ids": [pattern["pattern_id"]],
            "prioritized_hypothesis_ids": [hypothesis_id],
            "supporting_evidence_ids": refs,
            "opposing_evidence_ids": [],
            "limitations": ["Sem dados ou execução real de LLM."],
            "risks": ["Risco de falso negativo não estimado."],
            "recommended_tests": ["Aprovar teste temporal com especialistas."],
            "technical_dependencies": ["Ambiente de dados e gateway autorizados."],
            "human_decisions": ["Revisar evidências e critérios de refutação."],
            "next_steps": ["Validar em ambiente corporativo."],
            "fp_reduction_proven": False,
            "human_review_required": True,
        },
    }


class FixtureBackend:
    """Respostas FIXAS, sem LLM/rede; instanciado apenas por testes."""

    mode = "TEST_FIXTURE"
    model = "fixed-responses-for-tests"
    environment = "test"
    provider = "none"

    def __init__(self, responses=None):
        self.responses = outputs() if responses is None else responses
        self.calls = []

    def generate(self, *, stage, system, user, max_completion_tokens):
        self.calls.append(stage)
        value = self.responses[stage]
        if isinstance(value, Exception):
            raise value
        return ModelReply(value if isinstance(value, str) else json.dumps(value), 100, 50)
