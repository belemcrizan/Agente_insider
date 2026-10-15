"""Seis especialistas independentes, executados com dependências explícitas."""

from .critical_reviewer import CriticalReviewer
from .evidence_investigator import EvidenceInvestigator
from .executive_intelligence import ExecutiveIntelligence
from .hypothesis_generator import HypothesisGenerator
from .methodological_validator import MethodologicalValidator
from .risk_specialist import RiskSpecialist

AGENTS = (
    HypothesisGenerator(),
    EvidenceInvestigator(),
    CriticalReviewer(),
    MethodologicalValidator(),
    RiskSpecialist(),
    ExecutiveIntelligence(),
)
