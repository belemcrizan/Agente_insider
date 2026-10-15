"""Diagnóstico e inspeção locais, sem autenticação ou chamadas automáticas de dados."""

import argparse
import importlib.util
import json
from pathlib import Path

from .agents import AGENTS
from .contracts import EvidenceSnapshot, RunResult
from .data.evidence_builder import snapshot_identity
from .evaluation.metrics import technical_metrics
from .reporting import executive_markdown


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="agente_insider — investigação com revisão humana")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Dependências locais; não testa autenticação")
    schema = commands.add_parser("schema", help="Contrato de saída de um agente")
    schema.add_argument("stage", choices=[a.name for a in AGENTS])
    validate = commands.add_parser("validate-snapshot", help="Valida contrato e fingerprint local")
    validate.add_argument("path", type=Path)
    report = commands.add_parser("report", help="Imprime relatório local de um RunResult")
    report.add_argument("path", type=Path)
    metrics = commands.add_parser("metrics", help="Imprime métricas técnicas de um RunResult")
    metrics.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        value = {
            "packages": {
                name: importlib.util.find_spec(name) is not None
                for name in ("pandas", "pydantic", "boto3", "iaragenai")
            },
            "aws_authentication": "NOT_TESTED",
            "iara_authentication": "NOT_TESTED",
            "real_data_validation": "NOT_PERFORMED",
        }
    elif args.command == "schema":
        value = next(a for a in AGENTS if a.name == args.stage).output_model.model_json_schema()
    elif args.command == "validate-snapshot":
        snap = EvidenceSnapshot.model_validate_json(args.path.read_text(encoding="utf-8"))
        if snap.snapshot_id != snapshot_identity(snap):
            parser.error("Snapshot alterado ou fingerprint incompatível")
        value = {
            "snapshot_id": snap.snapshot_id,
            "contract_valid": True,
            "origin": snap.origin,
            "empirical_validation": "NOT_PERFORMED",
        }
    else:
        result = RunResult.model_validate_json(args.path.read_text(encoding="utf-8"))
        if args.command == "report":
            print(executive_markdown(result))
            return 0
        value = technical_metrics(result)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
