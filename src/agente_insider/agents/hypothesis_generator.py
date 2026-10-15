from ..contracts import HypothesisOutput
from .base import Agent


class HypothesisGenerator(Agent):
    name = "hypothesis_generator"
    output_model = HypothesisOutput
