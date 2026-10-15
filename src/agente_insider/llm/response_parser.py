"""JSON estrito: rejeita duplicatas, NaN, wrappers Markdown e campos extras."""

import json

from pydantic import ValidationError

from ..errors import ResponseContractError


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ResponseContractError("Chave JSON duplicada")
        result[key] = value
    return result


def _invalid_constant(_):
    raise ResponseContractError("Constante JSON inválida")


def parse_response(text: str, output_model, max_chars: int):
    if not isinstance(text, str) or not text.strip() or len(text) > max_chars:
        raise ResponseContractError("Resposta vazia ou acima do limite")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
        if not isinstance(value, dict):
            raise ResponseContractError("Resposta deve ser um objeto")
        return output_model.model_validate(value)
    except (ValueError, TypeError, ValidationError, RecursionError) as exc:
        # Nunca repetir conteúdo inválido, PII ou mensagens originais nos logs.
        raise ResponseContractError("Resposta fora do contrato") from exc
