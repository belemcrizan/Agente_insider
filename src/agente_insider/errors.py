"""Erros seguros: mensagens externas nunca são copiadas para a auditoria."""


class InsiderError(Exception):
    code = "INTERNAL_ERROR"


class DataContractError(InsiderError):
    code = "DATA_CONTRACT_ERROR"


class PolicyError(InsiderError):
    code = "POLICY_BLOCKED"


class ResponseContractError(InsiderError):
    code = "RESPONSE_CONTRACT_ERROR"


class AuthenticationFailure(InsiderError):
    code = "AUTHENTICATION_FAILED"


class TransientModelError(InsiderError):
    code = "TRANSIENT_MODEL_ERROR"


class ModelUnavailable(InsiderError):
    code = "MODEL_UNAVAILABLE"


class StageTimeout(InsiderError):
    code = "STAGE_TIMEOUT_NO_RETRY"


class QueryFailure(InsiderError):
    code = "QUERY_FAILED"
