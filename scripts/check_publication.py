"""Barreira adicional para o checkout público; não certifica ausência de todo dado sensível."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}
SUFFIXES = {".parquet", ".csv", ".xlsx", ".pem", ".key", ".log"}
SECRET = re.compile(
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def inspect(paths):
    errors = []
    for path in paths:
        relative = path.relative_to(ROOT)
        if set(relative.parts) & IGNORED or any(
            part.endswith(".egg-info") for part in relative.parts
        ):
            continue
        if path.suffix in SUFFIXES or (
            path.name.startswith(".env") and path.name != ".env.example"
        ):
            errors.append(f"Arquivo operacional não permitido: {relative}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Binário não revisado: {relative}")
            continue
        if SECRET.search(content):
            errors.append(f"Possível segredo: {relative}")
        if path.suffix == ".ipynb":
            for cell in json.loads(content).get("cells", []):
                if cell.get("outputs") or cell.get("execution_count") is not None:
                    errors.append(f"Notebook contém outputs/execuções: {relative}")
        if any(part in {"snapshots", "checkpoints", "artifacts"} for part in relative.parts):
            errors.append(f"Artefato operacional fora de tests: {relative}")
    return errors


def main():
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    # Verifica arquivos staged quando houver; antes do primeiro stage, verifica o checkout.
    paths = [ROOT / name.decode() for name in staged.split(b"\0") if name]
    if not paths:
        visible = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        paths = [ROOT / name.decode() for name in visible.split(b"\0") if name]
    errors = inspect(paths)
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Revisão automática de publicação: {len(paths)} arquivos inspecionados, sem bloqueios detectados."
    )


if __name__ == "__main__":
    main()
