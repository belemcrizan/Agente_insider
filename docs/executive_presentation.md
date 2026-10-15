# Apresentação executiva — roteiro

## 1. Problema e proposta

O monitoramento continua gerando alertas pelas regras atuais. A nova camada organiza evidências agregadas, formula hipóteses investigáveis, procura alternativas e apresenta testes para especialistas. O objetivo futuro é apoiar a investigação de falsos positivos sem elevar o risco de perder casos relevantes.

## 2. Funcionamento

Pipeline existente → snapshot de evidências → hipótese → investigação → contraprovas → avaliação metodológica → risco → síntese e revisão humana. Cada etapa possui contrato de saída e referências rastreáveis. Falha essencial bloqueia as etapas dependentes.

## 3. Entrega de engenharia

Pacote Python, adaptador do relatório existente, seis agentes independentes, gateway corporativo isolado, conector Athena/Glue opcional, notebook SageMaker, documentação e suíte automatizada. Os testes locais verificam controles técnicos com dados fabricados, sem afirmar acesso às bases corporativas ou execução real de LLM.

## 4. O que ainda não foi demonstrado

Não há hipótese empírica comprovada, classificação real FP/FN ou redução mensurada. Ainda é necessário validar no ambiente corporativo: o relatório real, a autenticação e compatibilidade IARA, autorização de envio, metadados das regras, histórico adjudicado e revisão dos especialistas.

## 5. Próximo experimento

Executar em sombra sobre recorte autorizado, com regras intactas. Revisores avaliam testabilidade, fidelidade às fontes, contraprovas, clareza e esforço. Comparar processo atual e configurações com diferentes números de agentes. Só avaliar ganhos FP/FN depois de definir e integrar os desfechos necessários.

## 6. Decisões solicitadas

- Quem valida fontes, recortes e metadados das regras?
- Qual aplicação/modelo IARA está autorizado e quem aprova transferência e retenção?
- Quais especialistas revisarão as hipóteses e com qual rubrica?
- Qual histórico permite avaliação temporal e monitoramento do risco de falso negativo?

O relatório executivo operacional é gerado por `executive_markdown(resultado)` depois da execução. Este documento é um roteiro de apresentação da solução, não um relatório de resultados corporativos.
