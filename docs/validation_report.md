# Relatório de validação local

Data: 2026-10-15. Ambiente: Linux, Python 3.12.14. Escopo: software local com dados fabricados, respostas fixas e clientes simulados. Não foram acessadas bases corporativas nem realizada autenticação IARA.

| Verificação | Resultado observado |
|---|---|
| `python -m pytest --cov=agente_insider --cov-report=term-missing` | 124 testes passaram; 978 de 1019 instruções cobertas (95,98%, arredondado a 96%) |
| Contratos dos seis agentes | Válidos no cenário fabricado; saídas/IDs/escopos inválidos bloqueados |
| Fluxo completo e falhas | Seis etapas em ordem; falha em qualquer etapa preserva anteriores e bloqueia dependentes |
| Autorização e privacidade | Ausência/expiração/escopo incompatível bloqueados; backend de teste não aceita origem real |
| Athena/Glue | Projeção, datas parametrizadas, paginação, truncamento, timeout e orçamento testados sem rede; shapes conferidos com botocore Stubber |
| IARA | Chamada e taxonomia de erros testadas com cliente simulado; SDK privado e autenticação não disponíveis |
| Auditoria e checkpoints | Testados em diretório temporário; não sobrescrita, cadeia de hashes e logs sem mensagem sensível original |
| `python -m ruff check .` | Passou |
| Notebook | Schema validado e sete células executadas sequencialmente em Python com AWS/IARA desabilitados |
| Kernel Jupyter local | Não executado com sucesso: host bloqueou sockets TCP e IPC; validação direta das células passou |
| Instalação editável | `python -m pip install -e '.[aws,dev,notebook]'` concluído |
| Build | `python -m build --no-isolation` gerou wheel e sdist |
| Revisão automática de publicação | Sem bloqueios detectados nos arquivos de código/documentação selecionados; notebook sem outputs |
| AWS e dados reais | Não executados; dependem do SageMaker/IAM/fontes reais |
| Redução de FP / risco de FN | Não medidos; dependem de histórico, método e avaliação humana |

## Dependências observadas

| Pacote | Versão local |
|---|---|
| pandas | 2.2.3 |
| pydantic | 2.13.5 |
| pytest / pytest-cov | 9.1.1 / 7.1.0 |
| boto3 | 1.43.114 |
| nbformat / nbclient | 5.11.1 / 0.11.0 |
| ruff | 0.17.1 |
| setuptools / build | 84.0.0 / 1.6.1 |

As faixas de dependências estão em `pyproject.toml`. Homologar/pinar as versões no ambiente corporativo antes de exigir reprodutibilidade entre hosts. Python 3.10 está declarado como suportado e configurado no workflow; o teste local foi feito somente em 3.12.

O build não valida o SDK corporativo. Cobertura não mede acurácia, segurança semântica ou qualidade de hipóteses. O notebook publicado não contém saídas desta execução nem dados de clientes. A cadeia de hashes é auditabilidade local, sem assinatura ou imutabilidade externa.
