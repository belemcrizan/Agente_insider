from ..contracts import CriticalOutput
from .base import Agent


class CriticalReviewer(Agent):
    name = "critical_reviewer"
    output_model = CriticalOutput
