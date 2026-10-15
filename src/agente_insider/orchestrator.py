"""Máquina sequencial: preflight → seis etapas → revisão humana; falha bloqueia dependentes."""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from pydantic import ValidationError

from .agents import AGENTS
from .config import OrchestratorConfig
from .contracts import EvidenceSnapshot, RunResult, StageMetric, utcnow
from .data.evidence_builder import snapshot_identity
from .data.quality import digest
from .errors import InsiderError, PolicyError, StageTimeout, TransientModelError
from .governance.audit import AuditTrail, CheckpointStore
from .governance.security import DataAuthorization, model_payload


class AgenteInsiderOrchestrator:
    def __init__(
        self,
        backend=None,
        *,
        config: OrchestratorConfig | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ):
        self.backend = backend
        self.config = config or OrchestratorConfig()
        self.store = checkpoint_store

    def pipeline_fingerprint(self):
        return digest(
            {
                "version": "0.1.0",
                "config": self.config.model_dump(),
                "prompts": {a.name: a.system_prompt for a in AGENTS},
                "backend": {
                    k: getattr(self.backend, k, None)
                    for k in ("mode", "model", "environment", "provider")
                },
            }
        )

    def _call(self, agent, system, user, timeout):
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="insider-gateway")
        future = executor.submit(
            self.backend.generate,
            stage=agent.name,
            system=system,
            user=user,
            max_completion_tokens=self.config.max_completion_tokens,
        )
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            # Não cancela uma chamada de transporte já em andamento: nunca repetir este caso.
            raise StageTimeout("Prazo da etapa excedido; resultado remoto desconhecido") from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def run(
        self, snapshot: EvidenceSnapshot, *, authorization: DataAuthorization | None = None
    ) -> RunResult:
        started = utcnow()
        run_id = "R-" + uuid.uuid4().hex
        stages, metrics = {}, []
        mode = getattr(self.backend, "mode", "NONE")
        fingerprint = self.pipeline_fingerprint()
        # Revalida mesmo objetos congelados (listas/dicts aninhados podem ser mutados).
        try:
            snapshot = EvidenceSnapshot.model_validate_json(snapshot.model_dump_json())
            if snapshot.snapshot_id != snapshot_identity(snapshot):
                raise PolicyError("Snapshot alterado depois de sua construção")
            if mode not in {"NONE", "IARA", "TEST_FIXTURE"}:
                raise PolicyError("Modo de execução desconhecido")
            if self.backend:
                if mode == "TEST_FIXTURE" and snapshot.origin != "TEST_FIXTURE":
                    raise PolicyError("Backend de testes não aceita dados reais")
                if mode == "IARA":
                    if snapshot.origin == "TEST_FIXTURE" or authorization is None:
                        raise PolicyError("Envio real requer snapshot real autorizado")
                    authorization.verify(
                        snapshot.snapshot_id,
                        environment=self.backend.environment,
                        provider=self.backend.provider,
                        model=self.backend.model,
                    )
            payload = model_payload(snapshot)
        except (InsiderError, ValidationError, ValueError) as exc:
            code = exc.code if isinstance(exc, InsiderError) else "SNAPSHOT_CONTRACT_ERROR"
            AuditTrail(run_id, snapshot.snapshot_id, None).emit(
                stage="preflight", status="FAILED", error_code=code
            )
            return self._result(
                run_id,
                snapshot.snapshot_id,
                started,
                "BLOCKED",
                mode,
                stages,
                self._skipped(AGENTS),
                fingerprint,
                code,
            )

        if self.store:
            self.store.start(
                run_id,
                snapshot,
                {
                    "run_id": run_id,
                    "pipeline_fingerprint": fingerprint,
                    "backend_mode": mode,
                    "approval_reference": authorization.approval_reference
                    if authorization
                    else None,
                },
            )
        audit = AuditTrail(run_id, snapshot.snapshot_id, self.store)
        audit.emit(stage="preflight", status="SUCCEEDED")
        if not self.backend or not payload["patterns"]:
            metrics = self._skipped(AGENTS)
            result = self._result(
                run_id,
                snapshot.snapshot_id,
                started,
                "EVIDENCE_ONLY",
                mode,
                stages,
                metrics,
                fingerprint,
            )
            audit.emit(stage="run", status="EVIDENCE_ONLY")
            if self.store:
                self.store.finish(result)
            return result

        error_code = None
        for index, agent in enumerate(AGENTS):
            stage_start = time.monotonic()
            attempts, reply = 0, None
            try:
                # Autorizações podem expirar durante uma execução longa.
                if mode == "IARA":
                    authorization.verify(
                        snapshot.snapshot_id,
                        environment=self.backend.environment,
                        provider=self.backend.provider,
                        model=self.backend.model,
                    )
                system, user = agent.build_messages(payload, stages, self.config)
                audit.emit(stage=agent.name, status="RUNNING")
                while True:
                    remaining = self.config.stage_timeout_seconds - (time.monotonic() - stage_start)
                    if remaining <= 0:
                        raise StageTimeout("Prazo excedido")
                    attempts += 1
                    try:
                        reply = self._call(agent, system, user, remaining)
                        break
                    except TransientModelError:
                        if attempts >= self.config.max_attempts:
                            raise
                        delay = self.config.retry_backoff_seconds * (2 ** (attempts - 1))
                        if (
                            time.monotonic() - stage_start + delay
                            >= self.config.stage_timeout_seconds
                        ):
                            raise StageTimeout("Retry excederia prazo") from None
                        time.sleep(delay)
                output = agent.validate(reply.text, payload, stages, self.config).model_dump(
                    mode="json"
                )
                if self.store:
                    self.store.checkpoint(run_id, index + 1, agent.name, output)
                stages[agent.name] = output
                audit.emit(stage=agent.name, status="SUCCEEDED", output_hash=digest(output))
                metrics.append(self._metric(agent.name, "SUCCEEDED", attempts, stage_start, reply))
            except Exception as exc:
                error_code = exc.code if isinstance(exc, InsiderError) else "INTERNAL_ERROR"
                audit.emit(stage=agent.name, status="FAILED", error_code=error_code)
                metrics.append(
                    self._metric(agent.name, "FAILED", attempts, stage_start, reply, error_code)
                )
                metrics.extend(self._skipped(AGENTS[index + 1 :]))
                break
        status = "BLOCKED" if error_code else "COMPLETE_STRUCTURALLY_VALIDATED"
        result = self._result(
            run_id,
            snapshot.snapshot_id,
            started,
            status,
            mode,
            stages,
            metrics,
            fingerprint,
            error_code,
        )
        audit.emit(stage="run", status=status, error_code=error_code)
        if self.store:
            self.store.finish(result)
        return result

    def _metric(self, stage, status, attempts, start, reply, error_code=None):
        input_tokens = reply.input_tokens if reply else None
        output_tokens = reply.output_tokens if reply else None
        cost = None
        if (
            input_tokens is not None
            and output_tokens is not None
            and self.config.input_price_per_million is not None
            and self.config.output_price_per_million is not None
        ):
            cost = (
                input_tokens * self.config.input_price_per_million
                + output_tokens * self.config.output_price_per_million
            ) / 1_000_000
        return StageMetric(
            stage=stage,
            status=status,
            attempts=attempts,
            elapsed_ms=(time.monotonic() - start) * 1000,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            error_code=error_code,
        )

    @staticmethod
    def _skipped(agents):
        return [
            StageMetric(stage=a.name, status="SKIPPED", attempts=0, elapsed_ms=0.0) for a in agents
        ]

    def _result(
        self, run_id, snapshot_id, started, status, mode, stages, metrics, fingerprint, code=None
    ):
        return RunResult(
            run_id=run_id,
            snapshot_id=snapshot_id,
            status=status,
            backend_mode=mode if mode in {"IARA", "TEST_FIXTURE"} else "NONE",
            started_at=started,
            finished_at=utcnow(),
            stages=stages,
            metrics=metrics,
            pipeline_fingerprint=fingerprint,
            cost_currency=self.config.currency,
            error_code=code,
        )
