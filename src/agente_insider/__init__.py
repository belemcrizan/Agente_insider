"""Investigação assistida; nenhuma ação sobre regras ou alertas."""

from .config import AdapterConfig, OrchestratorConfig
from .data.runreport_adapter import EvidenceAdapter
from .orchestrator import AgenteInsiderOrchestrator

__version__ = "0.1.0"
__all__ = ["AdapterConfig", "OrchestratorConfig", "EvidenceAdapter", "AgenteInsiderOrchestrator"]
