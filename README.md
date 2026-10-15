# agente_insider

Uma camada de inteligência investigativa com seis agentes para formular e contestar hipóteses sobre alertas PF/PJ, a partir de evidências agregadas e com revisão humana obrigatória.

**O código preserva as regras oficiais e não possui operações para encerrar, suprimir ou alterar alertas. Não há redução de falsos positivos comprovada.**

## O que esta versão entrega

- Adaptador para a interface já observada: `relatorio.results["PF"/"PJ"].cases`, sem consultar novamente o Athena.
- Agregação de indicadores numéricos, qualidade, proveniência e snapshots com fingerprint.
- Seis agentes com módulos, prompts versionados e contratos independentes.
- Orquestração sequencial, validação de referências, falha com bloqueio, retries limitados e checkpoints opcionais fora do Git.
- Gateway IARA isolado e conector Athena/Glue opcional, com projeção de colunas, parâmetros de datas, paginação, limite de linhas e verificação do workgroup.
- Notebook SageMaker, testes automatizados, métricas técnicas, rubrica humana e documentação.

**Estado real:** testes locais exercitam dados fabricados e clientes simulados. O `RunReport` corporativo, o acesso AWS e a autenticação/modelo IARA precisam ser validados no ambiente autorizado. O pipeline original `Config/run_all` não estava no repositório inspecionado; sua interface foi preservada por adaptação, sem inventar uma implementação substituta. Veja a [matriz de entrega](docs/delivery_matrix.md).

## Começar no SageMaker Studio / JupyterLab

No terminal do ambiente autorizado:

```bash
git clone https://github.com/belemcrizan/Agente_insider.git
cd Agente_insider
python -m pip install -e '.[aws,dev,notebook]'
python -m pytest -q
python -m agente_insider.cli doctor
```

Abra [notebooks/Agente_Insider_SageMaker.ipynb](notebooks/Agente_Insider_SageMaker.ipynb). O notebook executa em modo local por padrão e informa todas as integrações pendentes. Nenhuma fixture é usada como fallback. O SDK `iaragenai` deve ser instalado pelo canal corporativo aprovado; ele não é obtido de pacote público por esta instalação.

## Reutilizar o relatório existente

Execute o pipeline original no mesmo kernel. Em seguida:

```python
from agente_insider import EvidenceAdapter, AgenteInsiderOrchestrator

snapshot = EvidenceAdapter.from_runreport(
    relatorio,
    source_references=referencias_reais_pf_pj,  # dict com PF/PJ; metadados locais
    source_run_id=id_real_da_execucao_origem,
    complete_extract={"PF": False, "PJ": False},  # declare True só para recorte completo
)
resultado = AgenteInsiderOrchestrator().run(snapshot)
assert resultado.status == "EVIDENCE_ONLY"  # sem chamada de modelo
```

As variáveis acima vêm do pipeline real. Não há tabelas, fontes corporativas ou contagens históricas embutidas no projeto público. As únicas colunas conhecidas selecionadas pelo adaptador são `z_score_20dias_d0`, `z_score_20dias_d1` e `delta_z`. Se faltarem, o adaptador mantém a contagem e registra a lacuna.

## Executar os seis agentes com IARA

O notebook contém o fluxo completo de autenticação protegida com `getpass`, `DataAuthorization` vinculada ao snapshot/ambiente/modelo, `IaraBackend` e geração do dossiê. É necessário registrar uma aprovação real para transferir os agregados ao gateway; criar esse registro em código não concede permissão corporativa.

```python
# Dentro do contexto IaraGenAI já autenticado e autorizado:
from agente_insider.llm.iara_backend import IaraBackend

backend = IaraBackend(
    client, model=modelo_aprovado, allowed_models=frozenset({modelo_aprovado}), environment="dev"
)
resultado = AgenteInsiderOrchestrator(backend).run(snapshot, authorization=autorizacao_real)
```

`COMPLETE_STRUCTURALLY_VALIDATED` significa que as seis saídas passaram pelos contratos e verificações básicas. A verdade das interpretações, os testes de hipóteses e qualquer ganho de negócio ainda exigem validação humana/empírica. Falhas retornam `BLOCKED`, sem síntese de sucesso. Ausência de backend ou padrões elegíveis retorna `EVIDENCE_ONLY`.

## Documentação

| Documento | Conteúdo |
|---|---|
| [Inventário](docs/source_inventory.md) | O que foi realmente inspecionado e o que não estava disponível |
| [Arquitetura](docs/architecture.md) | Componentes, estados, falhas, custo e evolução |
| [Diagrama Mermaid](docs/architecture.mmd) | Importação no draw.io |
| [Contratos](docs/data_contracts.md) | Entradas, evidências, saídas e proveniência |
| [Operação](docs/operations.md) | SageMaker, configuração, IARA, diagnóstico e checkpoints |
| [Segurança](docs/security.md) | Autorização, minimização, limites e publicação |
| [Metodologia](docs/hypothesis_methodology.md) | Hipóteses, refutação e avaliação temporal |
| [Apresentação executiva](docs/executive_presentation.md) | Roteiro para liderança e decisões necessárias |
| [Matriz de entrega](docs/delivery_matrix.md) | Status, evidências, testes, pendências, riscos e próxima ação |
| [Validação local](docs/validation_report.md) | Comandos e resultados efetivamente executados |

## Validação e limites

```bash
python -m ruff check .
python -m pytest --cov=agente_insider --cov-report=term-missing
python -m build
python scripts/verify_notebook.py
python scripts/check_publication.py
```

Fixtures existem exclusivamente em `tests/fixtures/`. Não há backend sintético no pacote de produção. O limite de grupos (padrão 5) é uma minimização adicional, não garantia formal de anonimização. Texto livre de LLM ainda pode conter erro ou instruções indevidas e deve ser revisado. Timeout do orquestrador interrompe a espera e bloqueia as próximas etapas, mas não garante cancelamento de uma requisição já em andamento no SDK; configure também o transporte corporativo. Custo desconhecido é `null`, nunca zero presumido.
