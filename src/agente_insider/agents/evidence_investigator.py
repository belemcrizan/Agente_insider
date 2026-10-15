from ..contracts import InvestigationOutput
from .base import Agent


class EvidenceInvestigator(Agent):
    name = "evidence_investigator"
    output_model = InvestigationOutput
