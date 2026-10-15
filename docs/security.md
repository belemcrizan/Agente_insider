# Segurança e governança

## Fronteiras

Os agentes não recebem clientes de dados, shell, interpretador, SDK AWS ou ferramentas de escrita. O gateway só retorna texto. Consultas do conector são construídas pelo código a partir de identificadores validados e de um conjunto fixo de colunas. Datas usam parâmetros de execução. Não existe interface para executar SQL/código produzido pelo modelo.

As regras oficiais, os alertas e seus desfechos não são alterados. Os campos estruturados autorizam somente revisão humana. Texto livre ainda pode recomendar algo indevido; os controles estruturais não certificam a semântica de linguagem natural. A revisão humana e a ausência de atuadores são controles obrigatórios.

## Minimização e autorização

Somente indicadores numéricos conhecidos são lidos pelo adaptador. Dados extras no DataFrame não são serializados. O payload é reconstruído com campos allowlist e não contém fontes privadas, nomes de colunas extras, valores de triplas, identificadores ou instruções da base. Padrões/contagens pequenas são omitidos conforme contrato.

Agregados ainda podem permitir inferências, especialmente por comparação entre execuções. Não há anonimização formal. É necessária autorização corporativa de envio, destino, retenção e acesso. `DataAuthorization` é um registro verificável de escopo e validade; não é uma credencial, assinatura de aprovação ou mecanismo que concede permissão.

O gateway exige autorização vinculada ao snapshot, provider, ambiente e modelo em cada etapa. Fixtures não passam como dados reais e backend de teste não aceita snapshot real. Segredos pertencem ao ambiente ou ao mecanismo corporativo aprovado; nunca ao Git, logs ou notebook salvo.

## Prompt injection e saídas

Colunas livres e metadados de origem não entram nos prompts. Saídas anteriores continuam sendo dados não confiáveis. Prompts de sistema definem limites, enquanto parser, allowlists, schemas e validação cruzada fazem verificações determinísticas. Checks heurísticos detectam alguns formatos de CPF/CNPJ, e-mails, chaves e segredos nas saídas.

Essas defesas não garantem ausência de todo PII, prompt injection, informação fabricada ou instrução indevida. Uma referência válida pode acompanhar uma interpretação errada. Não há autorização operacional derivada do texto do modelo.

## Auditoria e persistência

Eventos contêm IDs técnicos, estado, hashes, tempo e código de falha; não incluem prompts, corpos inválidos, dados brutos ou mensagens de exceção. Checkpoints opcionais contêm somente snapshot agregado/metadados locais e saídas já validadas; ainda exigem proteção e retenção aprovadas. Diretórios são exclusivos, fora do Git; arquivos não são sobrescritos. Permissões 0700/0600 dependem de POSIX e não substituem ACLs, criptografia de disco ou política corporativa.

Cadeia de hashes não protege contra alguém com acesso administrativo que reescreva toda a cadeia. Não há assinatura ou armazenamento WORM. Configure logging do SDK e transporte de forma compatível com as políticas corporativas; a biblioteca não consegue controlar logs internos de terceiros.

## Publicação

O repositório de destino foi identificado como público. A publicação contém código genérico, documentação, notebook sem outputs e fixtures explicitamente fabricadas em testes. Não contém o prompt original, database/tabelas corporativas, contagens operacionais do pedido, nomes de clientes, snapshots reais, credenciais, resultados corporativos ou pacotes privados do SDK.

`.gitignore` e o verificador de publicação reduzem erros; acesso aos dados e revisão do conteúdo continuam obrigatórios. Não usar `git add -f` para incluir artefatos de investigação. A configuração de IAM, Lake Formation, S3/KMS e permissões do gateway permanece sob controle corporativo.
