# Inventário de fontes e interfaces

Inspeção em 2026-10-15. Destino: `belemcrizan/Agente_insider`, inicialmente vazio e público. Origem anterior: [belemcrizan/teste_teste](https://github.com/belemcrizan/teste_teste), commit `798cae1b0be1bd66efc872b9c704445704b73e1f`.

Foram lidos o README, `insider_ai/adapters.py`, `contracts.py`, `backends.py`, o notebook e os testes do projeto anterior, além do prompt fornecido. O repositório anterior permanece inalterado.

| Item | Evidência disponível | Decisão |
|---|---|---|
| `relatorio.results` | Adaptador anterior exige dict com PF/PJ | Aceitar Mapping contendo ambas as bases |
| `BaseResult.cases` | Acesso anterior a `.cases` com DataFrame | Preservar via protocolos; não importar classes ausentes |
| Indicadores | Três nomes de colunas no adaptador e no pedido | Selecionar somente esses nomes, sem inventar campos |
| `Config`, `run_all`, `AthenaRepository` original | Descritos no pedido; não encontrados no repositório anterior | Integrar pelo relatório; não reescrever o pipeline ausente |
| Esquemas Glue e tabelas corporativas | Descritos pelo usuário; sem acesso AWS neste ambiente | Configuração explícita privada e descoberta no SageMaker |
| Regras oficiais/metadados | Não fornecidos | Registrar lacuna; não inferir regras a partir de heurísticas |
| Desfechos históricos | Não fornecidos | `has_adjudicated_outcomes=false`; métricas FP/FN indisponíveis |
| SDK IARA | Interface fornecida e uso no código anterior | Gateway isolado; teste de contrato com cliente simulado |
| SDK/autenticação reais | Ausentes nesta execução | Não declarar execução real de LLM |

O adaptador anterior continha um snapshot de exemplo e o notebook podia usá-lo quando `relatorio` faltasse. Esta implementação exige fontes explícitas e não faz essa substituição. Contagens históricas fornecidas no pedido não são usadas como fixtures nem publicadas como resultados novos. Nenhum dado corporativo bruto ou resultado de cliente integra este repositório.
