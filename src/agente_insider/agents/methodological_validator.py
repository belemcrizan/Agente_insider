from ..contracts import MethodologicalOutput
from .base import Agent


class MethodologicalValidator(Agent):
    name = "methodological_validator"
    output_model = MethodologicalOutput
