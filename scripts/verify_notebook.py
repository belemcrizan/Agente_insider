"""Verifica notebook sem serviços; --kernel usa Jupyter quando o host permite sockets."""

import argparse
import contextlib
import io
import os
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", action="store_true", help="Executar com kernel Jupyter real")
    options = parser.parse_args(argv)
    path = ROOT / "notebooks" / "Agente_Insider_SageMaker.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    switches = dict(
        INSIDER_RUN_LOCAL_TESTS="0",
        INSIDER_SOURCE_MODE="runreport",
        INSIDER_RUN_ATHENA="0",
        INSIDER_RUN_IARA="0",
    )
    if options.kernel:
        from nbclient import NotebookClient

        client = NotebookClient(
            notebook, timeout=90, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}
        )
        client.execute(env={**os.environ, **switches})
    else:
        # Todas as células são Python comum, sem magics ou top-level await.
        previous = {key: os.environ.get(key) for key in switches}
        previous_cwd = Path.cwd()
        namespace = {"__name__": "__notebook_check__"}
        try:
            os.environ.update(switches)
            os.chdir(ROOT)
            with contextlib.redirect_stdout(io.StringIO()):
                for index, cell in enumerate(notebook.cells):
                    if cell.cell_type == "code":
                        exec(compile(cell.source, f"{path.name}:cell-{index}", "exec"), namespace)
            assert namespace["snapshot"] is None
            assert namespace["runtime_status"]["iara"] == "NOT_EXECUTED"
            assert namespace["runtime_status"]["athena"] == "NOT_EXECUTED"
        finally:
            os.chdir(previous_cwd)
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    count = sum(cell.cell_type == "code" for cell in notebook.cells)
    mode = "kernel Jupyter" if options.kernel else "Python direto, sem kernel Jupyter"
    print(
        f"Notebook: {count} células executadas ({mode}); AWS/IARA desabilitados; fonte real pendente."
    )


if __name__ == "__main__":
    main()
