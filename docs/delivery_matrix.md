# Matriz de entrega e critérios de aceite

Estado em 2026-10-15. **Implementação testada localmente não equivale a integração corporativa aceita.** Testes usam dados fabricados ou clientes simulados, identificados nos arquivos. A execução real de AWS/IARA e o relatório real não estavam acessíveis neste ambiente.

| Componente | Status real | Evidência de funcionamento | Testes executados | Dependências pendentes | Riscos | Próxima ação |
|---|---|---|---|---|---|---|
| Preservação do pipeline | Interface inspecionada; original não reescrito | Inventário do commit anterior; protocolos PF/PJ | Conversão sem mutação de DataFrames | `Config/run_all` e `RunReport` corporativo | Interface original pode ter detalhes adicionais | Executar adaptador sobre `relatorio` real |
| Adaptador de evidências | Implementado e validado localmente | Contagens, agrupamentos, lacunas e fingerprint estável | `tests/unit/test_adapter.py` | Recorte e referências reais | Float64 e seleção do recorte limitam interpretação | Conferir totais e linhagem no SageMaker |
| Qualidade e proveniência | Implementadas | Fonte, origem, completude e fingerprints por base | Nulos, infinitos, tipos, esquema e mutação | Metadados de regras e calendário reais | Fonte incompleta ou precisão inadequada | Validar esquema/completude com responsável |
| Hypothesis Generator | Módulo, prompt v1 e schema implementados | Critérios de refutação e referências exigidos | Contratos e fluxo com respostas fixas | Modelo IARA autenticado | Hipótese textual pode ser infundada | Testar e revisar saídas reais |
| Evidence Investigator | Implementado; sem SQL livre | Categorias de achado e lacunas tipadas | Cobertura e referências por hipótese | Histórico autorizado | Confundir inferência com observação | Conferir fidelidade com especialista |
| Critical Reviewer | Implementado | Alternativas, confundidores e contraprovas | Contratos, escopo e falha da etapa | Contexto real e revisão crítica | Contraprovas ausentes ou inventadas em texto | Avaliar qualidade da contestação |
| Methodological Validator | Implementado | Impede estado de validação empírica comprovada | Booleanos estritos e contrato | Desenho temporal e desfechos | Validação estrutural parecer comprovação | Revisar desenho e critérios de refutação |
| Risk Specialist | Implementado | Ação fechada em revisão humana; regras preservadas | Bloqueio de supressão/alteração e FP não comprovado | Avaliação humana de risco | Sem estimativa populacional de FN | Aprovar experimento em sombra |
| Executive Intelligence | Implementado | Síntese só após etapas essenciais válidas | Cobertura completa e alegações estruturadas | Julgamento humano | Texto livre ainda pode estar incorreto | Revisar dossiê antes de uso |
| Orquestrador | Implementado e exercitado ponta a ponta em testes | Seis etapas sequenciais, métricas e estados | Falha em cada etapa, retry, timeout e política | Transporte/gateway real | Chamada pode continuar após timeout local | Configurar prazo do SDK e executar em DEV |
| Backend IARA | Adaptador implementado; integração viva pendente | Chamada de SDK conferida com cliente simulado | `tests/unit/test_iara_backend.py` | SDK homologado, aplicação, credenciais e modelo | Assinatura/usage/retries podem variar por versão | Confirmar compatibilidade no canal corporativo |
| Athena/Glue opcional | Implementado; sem consulta AWS real nesta entrega | Projeção, parâmetros, paginação e controle do workgroup | Fakes e botocore Stubber com schemas instalados | IAM/Lake Formation, tabelas, workgroup/S3/KMS | LIMIT não limita leitura; recorte pode ser arbitrário | Preferir relatório existente; validar conector se necessário |
| Autorização e segurança | Controles determinísticos implementados | Snapshot/modelo/ambiente/validade e allowlists | Origem real versus fixture, PII e expiração | Aprovação corporativa e política de dados | Agregados e textos não garantem anonimização | Aprovar transferência/retenção no destino correto |
| Auditoria/checkpoints | Implementados e testados em diretório temporário | Arquivos exclusivos e cadeia de hashes | Não sobrescrita, integridade e sanitização | Diretório privado e retenção aprovados | Hash não substitui assinatura/WORM | Configurar armazenamento privado se necessário |
| Métricas e avaliação | Técnicas implementadas; negócio pendente | Latência, tokens quando fornecidos, custo opcional e rubrica humana | Estimativas, valores ausentes e revisão duplicada | Rótulos humanos e processo comparável | Cobertura de código não mede qualidade de LLM | Avaliar casos reais em sombra |
| Notebook SageMaker | Estrutura e sete células verificadas em Python | Importação, bloqueios e estados reais sem fallback | `scripts/verify_notebook.py` | Kernel/SDK/dados no SageMaker | Host local bloqueou sockets de Jupyter | Executar também `--kernel` no SageMaker |
| Pacote e CLI | Instalação e build locais verificados | Wheel/sdist, prompts incluídos e diagnóstico | Testes da CLI e importação do pacote | Ambiente corporativo homologado | Dependências podem diferir no destino | Instalar e executar doctor/testes |
| Documentação e diagrama | Entregues | Guias, metodologia, segurança, roteiro e Mermaid | Revisão de referências e conteúdo público | Aprovação da documentação interna adicional | Roteiro não é relatório de resultado real | Usar a documentação na validação com responsáveis |
| CI | Aprovado no GitHub em Python 3.10 e 3.12 | [Execução 38768885316](https://github.com/belemcrizan/Agente_insider/actions/runs/38768885316) concluída com sucesso | Instalação, lint, testes, notebook local, scanner e build nas duas versões | Nenhuma para a validação técnica desta versão | CI não acessa dados corporativos nem SDK privado | Manter os checks nas próximas alterações |

## Aceite técnico no ambiente real

O aceite de integração continua pendente até consumir o relatório real, conferir sua proveniência e executar os seis agentes com a aplicação IARA autenticada e os agregados autorizados. Revisores devem conferir evidências, contraprovas, lacunas e fidelidade da síntese. O software não possui aprovação para mudar regras ou tomar decisões sobre clientes.

## Aceite de negócio

Continua pendente. Exige desfechos adjudicados, comparação com processo atual, separação temporal, revisão humana e avaliação do risco de falso negativo. Não há percentual de redução de falsos positivos nesta entrega.
