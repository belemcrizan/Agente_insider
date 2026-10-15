# Metodologia de investigação e avaliação

Concentração de padrões e consistência do processamento não demonstram falsos positivos. Indicadores estatísticos exploratórios não são regras oficiais. Uma hipótese é uma explicação possível com condições de refutação e dados/testes necessários, não um desfecho de cliente.

## Sequência de evidência

1. Descrever o recorte, sua completude, fontes e qualidade.
2. Identificar padrões agregados, sem lhes atribuir causa ou rótulo FP/FN.
3. Formular hipóteses específicas, alternativas e critérios de refutação observáveis.
4. Separar evidência observada, inferência, contradição, informação ausente e teste pendente.
5. Contestar explicações e avaliar seleção, confundidores, vazamento e suficiência estatística.
6. Avaliar risco de falso negativo e desenho seguro em sombra, com monitoramento preservado.
7. Solicitar decisão humana sobre dados adicionais e experimentos futuros.

Testes sugeridos pelos agentes não são executados automaticamente. O conector Athena não executa consultas propostas em linguagem livre. Histórico de desfechos e regras documentadas exigem integração e contrato adicionais, sem inventar novas tabelas ou colunas.

## Avaliação técnica agora

Medir validade estrutural, referências, cobertura das hipóteses, êxito/falha por etapa, latência, tokens quando disponíveis, estimativa de custo apenas com preços conhecidos, bloqueios de política e preservação de checkpoints. A suíte automatizada usa dados fabricados para verificar comportamento do software. Ela não mede acurácia da LLM nem qualidade de hipóteses reais.

## Avaliação com especialistas

`HumanAssessment` registra revisão por hipótese/execução/revisor: investigabilidade, fidelidade das evidências (1–5), qualidade de refutação (1–5), cobertura de risco e tempo de investigação. Avaliações duplicadas do mesmo revisor são rejeitadas. A síntese é descritiva; sem observações, os valores ficam indisponíveis.

Compare o processo atual com um agente, três agentes e seis agentes em casos equivalentes, com revisão cega quando possível. Pré-defina rubricas e decisões de aceite antes de olhar os resultados. Quantidade de agentes não é métrica de qualidade.

## Quando houver histórico autorizado

Definir rótulos adjudicados, data do alerta e do desfecho, janela de observação e regras de inclusão. Separar rodadas de desenvolvimento das posteriores usadas para avaliação, evitando que decisões futuras vazem para a explicação do passado. Estratificar PF/PJ, períodos e grupos relevantes; verificar deriva, amostragem e cobertura.

Para propor redução de FP, é necessário denominador claro, comparação com processo atual e sensibilidade aos casos relevantes. FP entre alertas e taxa de falsos positivos na população são medidas diferentes. Medir risco de FN exige cobertura de casos relevantes, inclusive os que não foram alertados; um histórico contendo apenas alertas não basta para estimar FNR populacional.

Pré-definir tamanho amostral e intervalos de confiança apropriados ao desenho (por exemplo, intervalos binomiais em amostras independentes ou bootstrap por rodada/entidade quando houver dependência). Não calcular intervalos sobre contagens fabricadas nem divulgar ganhos sem rótulos e avaliação humana. As métricas FP/FN continuam `None` nesta versão.
