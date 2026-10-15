"""Reconstrói o notebook público sem dados, credenciais ou outputs."""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def main():
    markdown, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    cells = [
        markdown("""# agente_insider — SageMaker / JupyterLab

Investigação orientada por hipóteses, com seis agentes, evidências rastreáveis e revisão humana.
As regras oficiais permanecem intactas. Não há descarte automático nem ganho FP comprovado.

O modo padrão só verifica o ambiente. Não há dados de exemplo como fallback.
Para dados reais, use o `relatorio` do pipeline original no mesmo kernel ou habilite explicitamente
o conector Athena com configuração privada. IARA só executa mediante autorização de envio.

No terminal do ambiente, instale: `python -m pip install -e '.[aws,dev,notebook]'`.
Instale `iaragenai` somente pelo canal corporativo aprovado. Consulte `docs/operations.md`.
"""),
        code("""from pathlib import Path
import importlib.util
import os
import sys

PROJECT_ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents]
                     if (p / 'src' / 'agente_insider').is_dir()), None)
if PROJECT_ROOT is None:
    raise RuntimeError('Abra o notebook dentro do checkout Agente_insider.')
if str(PROJECT_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from agente_insider import EvidenceAdapter, AgenteInsiderOrchestrator
from agente_insider.evaluation.metrics import technical_metrics
from agente_insider.reporting import executive_markdown

RUN_LOCAL_TESTS = os.getenv('INSIDER_RUN_LOCAL_TESTS', '0') == '1'
SOURCE_MODE = os.getenv('INSIDER_SOURCE_MODE', 'runreport')
RUN_ATHENA = os.getenv('INSIDER_RUN_ATHENA', '0') == '1'
RUN_IARA = os.getenv('INSIDER_RUN_IARA', '0') == '1'
runtime_status = {'software_import': 'OK', 'automated_tests': 'NOT_EXECUTED',
                  'real_snapshot': 'NOT_LOADED', 'athena': 'NOT_EXECUTED',
                  'iara': 'NOT_EXECUTED', 'empirical_validation': 'PENDING'}
print('Pacote importado. Operações remotas dependem de habilitação explícita.')
print({name: importlib.util.find_spec(name) is not None for name in ('boto3', 'iaragenai')})
"""),
        markdown("""## 1. Verificação técnica opcional

Os testes automatizados usam exclusivamente fixtures fabricadas e clientes simulados.
Não representam execução de LLM, dados corporativos ou validação de hipóteses.
Defina `INSIDER_RUN_LOCAL_TESTS=1` para rodá-los; nenhum teste exige credencial.
"""),
        code("""if RUN_LOCAL_TESTS:
    import subprocess
    completed = subprocess.run([sys.executable, '-m', 'pytest', '-q'],
                               cwd=PROJECT_ROOT, check=False)
    runtime_status['automated_tests'] = 'PASSED' if completed.returncode == 0 else 'FAILED'
    if completed.returncode:
        raise RuntimeError('Testes técnicos falharam; corrija antes de avançar.')
else:
    print('Testes não executados nesta sessão. Comando: python -m pytest -q')
"""),
        markdown("""## 2. Consumir o `relatorio` já produzido

Execute o pipeline original neste kernel antes desta célula. Não há reexecução ou substituição
automática de `Config/run_all`. Configure no ambiente privado:
`INSIDER_SOURCE_PF`, `INSIDER_SOURCE_PJ` e `INSIDER_SOURCE_RUN_ID`.
Não imprima referências privadas. `INSIDER_COMPLETE_EXTRACT=1` só quando o recorte estiver completo.

O adaptador seleciona apenas os três indicadores numéricos conhecidos e produz agregados.
Não copia nomes, documentos, observações ou regras presentes nas linhas.
"""),
        code("""snapshot = None
resultado = None
if SOURCE_MODE == 'runreport':
    references_ready = all(os.getenv(key) for key in
                           ('INSIDER_SOURCE_PF', 'INSIDER_SOURCE_PJ', 'INSIDER_SOURCE_RUN_ID'))
    if 'relatorio' not in globals():
        print('PENDENTE: execute o pipeline original para obter relatorio neste kernel.')
    elif not references_ready:
        print('PENDENTE: configure metadados reais de origem no ambiente privado.')
    else:
        complete = os.getenv('INSIDER_COMPLETE_EXTRACT', '0') == '1'
        snapshot = EvidenceAdapter.from_runreport(
            globals()['relatorio'],
            source_references={'PF': os.environ['INSIDER_SOURCE_PF'],
                               'PJ': os.environ['INSIDER_SOURCE_PJ']},
            source_run_id=os.environ['INSIDER_SOURCE_RUN_ID'],
            complete_extract={'PF': complete, 'PJ': complete})
        runtime_status['real_snapshot'] = 'LOADED_FROM_RUNREPORT'
        print('Snapshot agregado preparado; nenhuma consulta adicional realizada.')
elif SOURCE_MODE != 'athena':
    raise RuntimeError('INSIDER_SOURCE_MODE deve ser runreport ou athena.')
"""),
        markdown("""## 3. Alternativa explícita: Athena e Glue

Use somente se não for reutilizar `relatorio`. Defina `INSIDER_SOURCE_MODE=athena`,
`INSIDER_RUN_ATHENA=1`, database, tabelas PF/PJ, workgroup e ID único da extração no ambiente.
O workgroup deve impor limite de leitura e destino de resultados criptografado.

Sem janela temporal, o limite de linhas não representa amostragem aleatória.
Para filtro de datas, configure `allowed_date_columns` e `DateWindow` com os nomes reais
descobertos no Glue; esta versão não presume a existência de uma coluna de data.
"""),
        code("""if SOURCE_MODE == 'athena' and RUN_ATHENA:
    required = ('INSIDER_DATABASE', 'INSIDER_TABLE_PF', 'INSIDER_TABLE_PJ',
                'INSIDER_WORKGROUP', 'INSIDER_SOURCE_RUN_ID')
    if not all(os.getenv(key) for key in required):
        print('BLOQUEADO: configuração privada Athena incompleta.')
        runtime_status['athena'] = 'BLOCKED_MISSING_CONFIG'
    else:
        from agente_insider.data.athena_repository import AthenaConfig, AthenaRepository
        cfg = AthenaConfig(database=os.environ['INSIDER_DATABASE'],
            tables={'PF': os.environ['INSIDER_TABLE_PF'], 'PJ': os.environ['INSIDER_TABLE_PJ']},
            workgroup=os.environ['INSIDER_WORKGROUP'], region=os.getenv('AWS_REGION', 'sa-east-1'))
        try:
            snapshot = AthenaRepository(cfg).snapshot(request_id=os.environ['INSIDER_SOURCE_RUN_ID'])
            runtime_status['real_snapshot'] = 'LOADED_FROM_ATHENA'
            runtime_status['athena'] = 'SUCCEEDED'
            print('Extração limitada concluída; metadados preservados no snapshot local.')
        except Exception as error:
            runtime_status['athena'] = 'FAILED'
            print('Athena bloqueado:', getattr(error, 'code', 'AWS_INITIALIZATION_FAILED'))
else:
    print('Conector Athena não executado nesta sessão.')
"""),
        markdown("""## 4. Validar evidências sem chamar IARA

O estado `EVIDENCE_ONLY` confirma somente o processamento de evidências disponíveis.
Histórico de desfechos e metadados de regras continuam ausentes neste contrato.
"""),
        code("""if snapshot is not None:
    evidencia_apenas = AgenteInsiderOrchestrator().run(snapshot)
    print('Estado:', evidencia_apenas.status)
    print('Lacunas:', sorted({q.code for q in snapshot.quality}))
else:
    print('Nenhuma evidência real carregada. Nenhum exemplo foi substituído.')
"""),
        markdown("""## 5. Autorização e execução real IARA

Defina `INSIDER_RUN_IARA=1` somente após aprovação real do envio dos agregados.
Metadados obrigatórios: `INSIDER_APPROVED_BY`, `INSIDER_APPROVAL_REFERENCE`,
`INSIDER_APPROVAL_EXPIRES_AT` (ISO 8601 com timezone), `IARA_MODEL`, `IARA_ALLOWED_MODELS`
(lista por vírgula), `IARA_ENVIRONMENT` e `IARA_PROVIDER`.

O registro fica vinculado a este snapshot, modelo e ambiente. Não concede permissão corporativa.
Client ID/Secret são obtidos por `getpass`; não cole segredos em células.
Compatibilidade do SDK e autenticação reais precisam ser confirmadas neste ambiente.
Configure timeout/retries do transporte corporativo; um timeout local não cancela a chamada remota.
"""),
        code("""if RUN_IARA and snapshot is not None:
    required = ('INSIDER_APPROVED_BY', 'INSIDER_APPROVAL_REFERENCE',
                'INSIDER_APPROVAL_EXPIRES_AT', 'IARA_MODEL', 'IARA_ALLOWED_MODELS',
                'IARA_ENVIRONMENT', 'IARA_PROVIDER')
    cid = secret = client = None
    if not all(os.getenv(key) for key in required):
        print('BLOQUEADO: metadados de autorização IARA incompletos.')
        runtime_status['iara'] = 'BLOCKED_MISSING_AUTHORIZATION'
    else:
        try:
            from datetime import datetime
            from getpass import getpass
            from iaragenai import IaraGenAI
            from agente_insider.governance.security import DataAuthorization
            from agente_insider.llm.iara_backend import IaraBackend

            authorization = DataAuthorization(
                snapshot_id=snapshot.snapshot_id, approved_by=os.environ['INSIDER_APPROVED_BY'],
                approval_reference=os.environ['INSIDER_APPROVAL_REFERENCE'],
                expires_at=datetime.fromisoformat(os.environ['INSIDER_APPROVAL_EXPIRES_AT']),
                environment=os.environ['IARA_ENVIRONMENT'], provider=os.environ['IARA_PROVIDER'],
                model=os.environ['IARA_MODEL'])
            authorization.verify(snapshot.snapshot_id, environment=os.environ['IARA_ENVIRONMENT'],
                                 provider=os.environ['IARA_PROVIDER'], model=os.environ['IARA_MODEL'])
            cid, secret = getpass('IARA Client ID: ').strip(), getpass('IARA Client Secret: ').strip()
            if not cid or not secret:
                raise RuntimeError('Credenciais não preenchidas.')
            with IaraGenAI(client_id=cid, client_secret=secret,
                          environment=os.environ['IARA_ENVIRONMENT'],
                          provider=os.environ['IARA_PROVIDER']) as client:
                backend = IaraBackend(client, model=os.environ['IARA_MODEL'],
                    allowed_models=frozenset(m.strip() for m in os.environ['IARA_ALLOWED_MODELS'].split(',')),
                    environment=os.environ['IARA_ENVIRONMENT'], provider=os.environ['IARA_PROVIDER'])
                resultado = AgenteInsiderOrchestrator(backend).run(snapshot, authorization=authorization)
            runtime_status['iara'] = resultado.status
            print(technical_metrics(resultado))
            print(executive_markdown(resultado))
        except Exception as error:
            runtime_status['iara'] = 'FAILED'
            print('IARA não concluído:', getattr(error, 'code', 'IARA_INITIALIZATION_FAILED'))
        finally:
            cid = secret = client = None
elif RUN_IARA:
    runtime_status['iara'] = 'BLOCKED_NO_REAL_SNAPSHOT'
    print('BLOQUEADO: não há snapshot real para o gateway.')
else:
    print('IARA não executado nesta sessão. Nenhum sucesso de LLM foi presumido.')
"""),
        markdown("""## 6. Estado desta sessão e próximos passos

Os resultados ficam em memória. Checkpoints são opcionais e exigem diretório privado fora do Git
e autorização de retenção; veja o guia operacional. Para avançar, valide as fontes reais,
a compatibilidade IARA e as interpretações com especialistas. Testes sugeridos não foram executados.

Antes de publicar qualquer alteração, limpe outputs e execute `scripts/check_publication.py`.
"""),
        code("""for component, state in runtime_status.items():
    print(f'{component}: {state}')
print('Regras preservadas; revisão humana obrigatória; redução de FP não comprovada.')
"""),
    ]
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
    )
    # IDs determinísticos permitem reconstrução sem ruído no Git.
    for index, cell in enumerate(notebook.cells):
        cell.id = f"insider-{index:02d}"
    nbf.validate(notebook)
    nbf.write(notebook, ROOT / "notebooks" / "Agente_Insider_SageMaker.ipynb")


if __name__ == "__main__":
    main()
