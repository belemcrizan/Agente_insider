# Contratos de dados

Os modelos Pydantic v2 proíbem campos extras, restringem tipos e têm versão de schema. Todas as evidências são agregadas. Texto e identificadores de clientes, transações, datas livres, nomes de regras e observações do DataFrame não são copiados ao modelo.

## Entrada existente

`EvidenceAdapter.from_runreport` exige `relatorio.results` com PF/PJ; cada item deve possuir `.cases` como pandas DataFrame. O operador fornece `source_references`, `source_run_id` e, se puder comprovar, `complete_extract`. Sem declaração explícita, a extração é considerada incompleta.

Nomes das três colunas numéricas são normalizados sem distinguir maiúsculas/minúsculas; colisões são rejeitadas. Strings numéricas são convertidas para float64. Nulos, conteúdo não numérico e infinitos contam como triplas inválidas. Nenhum limiar estatístico ou rótulo exploratório é tratado como regra oficial. Repetições usam os três valores dessa representação numérica, sem arredondamento decimal adicional. Dados de origem com precisão superior a float64 exigem avaliar a perda de precisão antes de usar os agrupamentos.

## Snapshot local versus payload do modelo

| Campo | Snapshot local | Payload do modelo |
|---|---|---|
| Origem, `snapshot_id`, versão | Sim | Sim |
| Referência de tabela e execução de origem | Sim, fornecida pelo operador | Não |
| Query ID, bytes lidos e completude | Sim, quando conector usado | Somente completude agregada |
| Fingerprints do esquema/conteúdo | Sim | Não, exceto identidade do snapshot |
| Alert count, triplas válidas/inválidas, cardinalidade e maior grupo | Sim | Só métricas allowlist que passam a projeção |
| Padrões: ID opaco, escopo, contagem e referências | Sim | Somente grupos com tamanho mínimo |
| Valores reais das triplas e linhas originais | Não | Não |
| Regras, desfechos e classificações FP/FN | Não disponíveis | Ausência explícita |

Grupos abaixo de `min_group_size` não produzem padrões. Escopos pequenos não são enviados. Contagens positivas abaixo do mínimo também são omitidas do payload. Isso reduz exposição, mas não implementa privacidade diferencial, k-anonimato formal ou proteção contra inferência por diferenças de agregados.

`Evidence` contém `evidence_id`, escopo, métrica allowlist, contagem e índice da fonte. `Pattern` referencia evidências do mesmo escopo. `SourceProfile` registra fingerprint e completude. `QualityIssue` usa códigos fechados: falta de indicadores, valores inválidos, escopo vazio/pequeno, truncamento, recorte incompleto e ausência de histórico/metadados de regras.

## Saídas dos seis agentes

Cada módulo usa seu próprio schema: `HypothesisOutput`, `InvestigationOutput`, `CriticalOutput`, `MethodologicalOutput`, `RiskOutput` e `ExecutiveOutput`. Obtenha JSON Schema com `agente-insider schema NOME_DA_ETAPA`.

Hipóteses exigem padrão de origem, referências, alternativas, lacunas, testes e critérios de refutação, com `empirical_status=UNTESTED`. As quatro revisões cobrem todas as hipóteses exatamente uma vez. O executivo prioriza todas elas. IDs inexistentes, duplicados ou hipóteses omitidas bloqueiam o fluxo. Não se permite ação fora de `HUMAN_REVIEW_ONLY`, supressão automática, alteração de regras ou alegação estruturada de validação empírica/redução de FP.

O parser rejeita JSON com chaves duplicadas, `NaN`, infinitos, raiz não objeto, Markdown e respostas extensas. A validação de IDs confirma a existência da fonte, mas não que a interpretação textual seja verdadeira ou sustentada: especialistas devem revisar a fidelidade das afirmações.
