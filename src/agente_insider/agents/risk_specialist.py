from ..contracts import RiskOutput
from .base import Agent


class RiskSpecialist(Agent):
    name = "risk_specialist"
    output_model = RiskOutput
