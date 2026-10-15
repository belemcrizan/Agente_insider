# Instalação e operação no SageMaker

## Preparar o ambiente

Clone o repositório no terminal do SageMaker Studio, instale `.[aws,dev,notebook]` com o Python do kernel e abra `notebooks/Agente_Insider_SageMaker.ipynb`. Python mínimo: 3.10. O notebook também localiza `src/` para importação em um checkout recém-clonado.

Não use `pip install iaragenai` a partir de uma origem desconhecida. Instale a versão corporativa homologada pelo canal aprovado. A interface de referência veio do pedido e do código anterior, com versão observada 0.44.1; a compatibilidade, os parâmetros de tokens, o timeout de transporte e os retries do SDK ainda devem ser verificados localmente.

`python -m agente_insider.cli doctor` só informa dependências; não realiza autenticação ou leitura AWS. Os testes usam exclusivamente dados fabricados e clientes simulados. `scripts/verify_notebook.py` valida o formato e executa todas as células Python em um namespace local, descartando saídas. Use `--kernel` para executar também por um kernel Jupyter quando o host permitir sockets. Nenhum dos modos equivale à execução corporativa.

## Caminho principal: reutilizar o pipeline

No mesmo kernel em que o pipeline produz `relatorio`, configure referências e o ID real de origem. Passe o objeto diretamente a `EvidenceAdapter.from_runreport`. A conversão não faz nenhuma chamada de rede nem altera os DataFrames originais.

Se `relatorio` não estiver disponível, o notebook informa a pendência. Não cria dados substitutos. É possível executar a célula do pipeline original nesse notebook ou chamar o adaptador diretamente no notebook original depois de incluir o pacote.

Os nomes privados de database/tabelas devem ser definidos somente no ambiente autorizado. `complete_extract=True` deve significar que todas as linhas do recorte declarado foram obtidas; não significa necessariamente toda a população. Se o pipeline tiver um limite ou recorte desconhecido, mantenha `False`.

## Alternativa: consultar Athena/Glue

Configure no ambiente, sem incluir esses valores no Git:

- `INSIDER_DATABASE`, `INSIDER_TABLE_PF`, `INSIDER_TABLE_PJ`.
- `INSIDER_WORKGROUP`: grupo existente, habilitado, que imponha saída criptografada e teto de leitura dentro de `max_scan_bytes`.
- Região AWS aprovada e papel IAM/Lake Formation existente.

```python
import os
from agente_insider.data.athena_repository import AthenaConfig, AthenaRepository

config = AthenaConfig(
    database=os.environ["INSIDER_DATABASE"],
    tables={"PF": os.environ["INSIDER_TABLE_PF"], "PJ": os.environ["INSIDER_TABLE_PJ"]},
    workgroup=os.environ["INSIDER_WORKGROUP"],
    region=os.getenv("AWS_REGION", "sa-east-1"),
)
repo = AthenaRepository(config)
snapshot = repo.snapshot(request_id=id_real_e_unico_da_extracao)
```

`DateWindow` aceita início inclusivo e fim exclusivo. Uma coluna de filtro precisa ser aprovada em `allowed_date_columns` e descoberta como date/timestamp. Nenhum nome de coluna de data é presumido. Prefira janelas compatíveis com partições reais. `LIMIT max_rows+1` detecta truncamento; isso não evita leitura de muitos bytes nem representa amostragem aleatória. PF/PJ são lidos em consultas separadas, sem garantia de snapshot transacional conjunto.

Permissões mínimas devem ser restritas aos recursos aprovados: Glue GetTable, Athena GetWorkGroup/StartQueryExecution/GetQueryExecution/GetQueryResults/StopQueryExecution e leitura dos dados/resultado S3, com KMS/Lake Formation quando exigidos. Athena grava resultados SELECT no destino do workgroup; isso não modifica os dados de origem. O projeto não concede IAM nem cria buckets, workgroups ou tabelas.

## Gateway e autorização

Antes da chamada real, confirme acesso ao modelo autorizado, aplicação/ambiente corretos e autorização de envio dos agregados. Registre `approved_by`, `approval_reference`, `snapshot_id`, modelo, provider, ambiente e validade com timezone em `DataAuthorization`. O notebook aceita esses metadados via variáveis de ambiente; não deduz autorização da existência de credenciais.

O ID/segredo são solicitados com `getpass`; use o gerenciador corporativo de segredos quando disponível. O contexto `IaraGenAI` é aberto externamente e passado ao backend. Se falhar antes do orquestrador, o notebook imprime somente o tipo seguro da falha e não declara execução de agente. Não compartilhe tracebacks contendo requisições ou credenciais.

Se houver erro de autenticação como o já relatado para a aplicação, valide ambiente, vínculo e habilitação com a equipe responsável. Não faça retries de autenticação nem substitua o gateway por serviço externo.

## Artefatos e diagnóstico

Sem `CheckpointStore`, o resultado fica em memória e os eventos vão ao logger da biblioteca. Persistência é opcional, requer referência de autorização e diretório fora de qualquer checkout Git. O destino deve ter acesso/retenção aprovados; checkpoints contêm agregados e texto que ainda podem ser confidenciais.

```python
from agente_insider.governance.audit import CheckpointStore

store = CheckpointStore(diretorio_privado_aprovado, approval_reference=aprovacao_de_retencao)
orchestrator = AgenteInsiderOrchestrator(backend, checkpoint_store=store)
resultado = orchestrator.run(snapshot, authorization=autorizacao_real)
```

Não há retomada automática. Para investigar falha, confira `status`, `error_code`, métricas e checkpoints validados. Corrija a causa no ambiente e crie uma nova execução. Respostas inválidas e mensagens originais de exceções não são registradas. Uma falha de persistência pode interromper a própria função: não interprete ausência de `result.json` como sucesso.

| Código/estado | Interpretação | Ação |
|---|---|---|
| `EVIDENCE_ONLY` | Sem backend ou padrões elegíveis | Inspecionar qualidade e configuração |
| `POLICY_BLOCKED` | Autorização, minimização ou política incompatível | Corrigir somente com aprovação real |
| `AUTHENTICATION_FAILED` | Gateway recusou acesso | Revisar aplicação/ambiente no canal corporativo |
| `RESPONSE_CONTRACT_ERROR` | JSON, campos ou referências inválidos | Revisar prompt/resposta no ambiente seguro |
| `STAGE_TIMEOUT_NO_RETRY` | Prazo excedido, resultado remoto desconhecido | Verificar transporte e custo antes de nova execução |
| `MODEL_UNAVAILABLE` | SDK/modelo indisponível ou incompatível | Verificar versão e compatibilidade |
| `INTERNAL_ERROR` | Falha inesperada sanitizada | Diagnosticar com acesso restrito, sem publicar conteúdo |

Antes de commits, limpe todas as saídas do notebook e execute `python scripts/check_publication.py`. Esse verificador é uma barreira adicional, não uma garantia contra todos os tipos de informação sensível.
