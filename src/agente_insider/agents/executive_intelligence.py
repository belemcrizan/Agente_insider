from ..contracts import ExecutiveOutput
from .base import Agent


class ExecutiveIntelligence(Agent):
    name = "executive_intelligence"
    output_model = ExecutiveOutput
