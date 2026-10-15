# Arquitetura e decisões

O processo roda como biblioteca Python no SageMaker. Não cria serviços adicionais, tabelas, recursos de infraestrutura ou persistência remota. O caminho principal reaproveita `RunReport` em memória; o conector Athena/Glue é uma alternativa quando a extração original não estiver disponível.

## Responsabilidades

| Camada | Implementação | Limite |
|---|---|---|
| Leitura | `data/runreport_adapter.py`, `athena_repository.py` | Sem SQL livre de LLM; fontes configuradas pelo operador |
| Evidência | `quality.py`, `evidence_builder.py` | Somente contagens e padrões; nenhuma regra oficial deduzida |
| Inteligência | Seis módulos em `agents/`, prompts v1 | Hipóteses e testes propostos, sem execução operacional |
| Orquestração | `orchestrator.py` | Sequência obrigatória; erro bloqueia dependentes |
| Gateway | `llm/iara_backend.py` | Sessão autenticada externamente; nenhuma credencial persistida |
| Governança | `governance/` | Escopo de autorização, referências, auditoria e proteção básica |
| Avaliação | `evaluation/` | Técnica agora; valor de negócio requer rótulos humanos |

## Estados e tratamento de falhas

Preflight revalida o contrato e o fingerprint do snapshot, restringe a projeção e verifica a autorização. Ausência de modelo ou de padrões elegíveis produz `EVIDENCE_ONLY`, com todas as seis etapas `SKIPPED`. Uma execução do modelo só termina como `COMPLETE_STRUCTURALLY_VALIDATED` depois das seis saídas válidas. Qualquer falha essencial produz `BLOCKED`; etapas já validadas são preservadas, a falha fica em `FAILED` e dependentes em `SKIPPED`.

Autenticação, permissão, saída inválida e erros desconhecidos não são repetidos. Somente códigos explicitamente transitórios do gateway podem receber retries, até o limite configurado. O prazo cobre tentativas e backoff da etapa. Timeout encerra a espera local, sem retry, e impede novas chamadas; uma requisição já iniciada pode continuar em uma thread até o transporte encerrar. Configure timeouts e retries também no SDK corporativo. Não há garantia de cancelamento remoto nem de faturamento exatamente uma vez.

## Identidade, checkpoints e reprodução

`snapshot_id` deriva dos metadados locais, indicadores relevantes, qualidade e agregados. Valores de indicadores só participam de fingerprints e agrupamentos locais; não integram o payload. A ordem das linhas não altera a identidade. `run_id` é único por tentativa completa, pois uma nova execução de LLM pode ter resultados distintos.

`pipeline_fingerprint` inclui versão, configuração, modelo, ambiente e texto/schema de cada prompt. Checkpoints opcionais usam diretórios exclusivos, arquivos criados com `O_EXCL`, permissões POSIX restritas e hashes nas trilhas de eventos. A cadeia detecta alterações acidentais; não é assinatura criptográfica nem armazenamento imutável contra um administrador. Não há retomada automática nem reutilização silenciosa de saídas antigas.

## Controle de volume e custo

Há limite de linhas por base, padrões, hipóteses, caracteres de contexto/resposta, tokens de conclusão, tentativas e prazo. Não se trunca silenciosamente o contexto. O payload cresce com saídas anteriores; se exceder o limite, a execução bloqueia.

No Athena, `LIMIT` limita o resultado, não os bytes lidos. O conector exige workgroup existente, habilitado, com configuração imposta, limite de bytes dentro do orçamento e resultado criptografado. Datas usam `ExecutionParameters` e colunas previamente aprovadas. Os resultados de SELECT usam o local S3 já configurado no workgroup; fontes e tabelas permanecem inalteradas. Sem janela temporal, um recorte limitado pode ser arbitrário e não é apropriado para conclusões populacionais.

Tokens são medidos apenas se o gateway os fornecer. Preços aprovados são opcionais; valores ausentes geram custo `null`. Custos de tentativas sem usage e faturamento Athena não são estimados como zero. A cifra por resposta é uma estimativa, não uma fatura.

## Evolução condicionada à necessidade

Histórico rotulado, calendário de rodadas, regras documentadas e contexto operacional exigem novo contrato com dados reais e aprovação específica. S3 para checkpoints, CloudWatch, Step Functions ou execução agendada só devem ser considerados após necessidade operacional, requisitos de retenção e autorização. Comparar processo atual, um agente, três agentes e seis agentes antes de atribuir valor à complexidade adicional.

O arquivo [architecture.mmd](architecture.mmd) pode ser importado em draw.io: Arrange → Insert → Advanced → Mermaid. Não contém HTML ou configuração específica do renderizador.
