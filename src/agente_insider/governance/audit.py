"""Checkpoints locais exclusivos e eventos encadeados, sem corpo de prompts nos logs."""

import json
import logging
import os
from pathlib import Path

from ..contracts import Identifier, utcnow
from ..data.quality import digest
from ..errors import PolicyError

LOGGER = logging.getLogger("agente_insider.audit")


class CheckpointStore:
    def __init__(self, root: Path | str, *, approval_reference: str):
        if not isinstance(approval_reference, str) or not approval_reference.strip():
            raise PolicyError("Persistência requer referência de autorização")
        self.root = Path(root).resolve()
        if any((parent / ".git").exists() for parent in [self.root, *self.root.parents]):
            raise PolicyError("Checkpoints devem ficar fora de repositórios Git")

    def start(self, run_id: str, snapshot, manifest: dict):
        from pydantic import TypeAdapter

        TypeAdapter(Identifier).validate_python(run_id)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = self.root / run_id
        directory.mkdir(mode=0o700, exist_ok=False)
        self._write(directory / "manifest.json", manifest)
        self._write(directory / "snapshot.json", snapshot.model_dump(mode="json"))

    @staticmethod
    def _write(path: Path, value: dict):
        content = json.dumps(
            value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2
        ).encode("utf-8")
        # O_EXCL não sobrescreve checkpoints anteriores; 0600 em POSIX.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

    def checkpoint(self, run_id: str, index: int, stage: str, output: dict):
        self._write(self.root / run_id / f"{index:02d}_{stage}.json", output)

    def finish(self, result):
        self._write(self.root / result.run_id / "result.json", result.model_dump(mode="json"))

    def append_event(self, run_id: str, event: dict):
        path = self.root / run_id / "events.jsonl"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")


class AuditTrail:
    def __init__(self, run_id: str, snapshot_id: str, store: CheckpointStore | None):
        self.run_id, self.snapshot_id, self.store = run_id, snapshot_id, store
        self.previous_hash = "0" * 64
        self.events = []

    def emit(
        self,
        *,
        stage: str,
        status: str,
        output_hash: str | None = None,
        error_code: str | None = None,
    ):
        event = dict(
            sequence=len(self.events),
            run_id=self.run_id,
            snapshot_id=self.snapshot_id,
            timestamp=utcnow().isoformat(),
            stage=stage,
            status=status,
            output_hash=output_hash,
            error_code=error_code,
            previous_hash=self.previous_hash,
        )
        event["event_hash"] = digest(event)
        if self.store:
            self.store.append_event(self.run_id, event)
        LOGGER.info(json.dumps(event, sort_keys=True))
        self.events.append(event)
        self.previous_hash = event["event_hash"]


def verify_event_chain(events: list[dict]) -> bool:
    previous_hash = "0" * 64
    for index, event in enumerate(events):
        value = {k: v for k, v in event.items() if k != "event_hash"}
        if (
            event.get("sequence") != index
            or event.get("previous_hash") != previous_hash
            or event.get("event_hash") != digest(value)
        ):
            return False
        previous_hash = event["event_hash"]
    return True
