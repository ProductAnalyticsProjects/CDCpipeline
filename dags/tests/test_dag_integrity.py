"""Test di integrità dei DAG Airflow.

Non serve un cluster Airflow acceso per questi test: `DagBag` importa i file
Python in dags/ e li istanzia in memoria, esattamente come farebbe lo
scheduler. Questo basta per intercettare la classe di errori più comune e
più fastidiosa da scoprire tardi: un DAG con un errore di sintassi/import
che lo scheduler scarta silenziosamente, mostrando "DAG non trovato" in UI
senza dire perché.

Gira in CI nel job `dag-integrity` (ci.yml), separato dal job `test` perché
usa un ambiente Python diverso (Airflow, non PySpark) e non ha bisogno di Java.
"""

import os
from pathlib import Path

import pytest
from airflow.models import DagBag

DAGS_DIR = Path(__file__).resolve().parent.parent

# Airflow calcola self-check "no DAG più vecchio di N secondi non ricaricato":
# irrilevante in CI, dove importiamo una volta sola. Lo disattiviamo per non
# dipendere da una variabile d'ambiente non impostata sul runner.
os.environ.setdefault("AIRFLOW__CORE__DAGBAG_IMPORT_TIMEOUT", "60")


@pytest.fixture(scope="session")
def dagbag():
    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_no_import_errors(dagbag):
    """Se un DAG ha un errore di import (typo, dipendenza mancante,
    IndentationError...), DagBag non solleva un'eccezione: lo registra in
    `import_errors` e va avanti. Va controllato esplicitamente."""
    assert not dagbag.import_errors, f"Errori di import nei DAG: {dagbag.import_errors}"


def test_dags_were_found(dagbag):
    """Guardia contro un path sbagliato che farebbe passare il test
    precedente 'a vuoto' (nessun errore perché nessun DAG è stato caricato)."""
    assert len(dagbag.dags) >= 2, f"Attesi almeno 2 DAG, trovati: {list(dagbag.dags)}"


def test_no_cycles(dagbag):
    """DagBag rifiuta già un DAG ciclico al momento del load (non finirebbe
    in dagbag.dags). Qui lo verifichiamo esplicitamente chiamando
    topological_sort(), che solleva se il grafo non è un DAG valido —
    così il test fallisce con un messaggio chiaro invece di un conteggio
    dei DAG silenziosamente più basso del previsto."""
    for dag_id, dag in dagbag.dags.items():
        dag.topological_sort()


@pytest.mark.parametrize("field", ["owner", "retries"])
def test_default_args_present(dagbag, field):
    """Ogni DAG deve dichiarare owner (per sapere chi contattare quando fallisce
    alle 3 di notte) e retries (i job di questo progetto dipendono da Docker/
    rete tra container: un fallimento transitorio non deve richiedere un
    intervento manuale)."""
    for dag_id, dag in dagbag.dags.items():
        value = dag.default_args.get(field)
        assert value not in (None, ""), f"DAG '{dag_id}' non imposta '{field}'"
        if field == "retries":
            assert value >= 1, f"DAG '{dag_id}' ha retries={value}, atteso >= 1"


def test_no_catchup_by_default(dagbag):
    """catchup=True su un DAG con start_date nel passato lancia in raffica
    una run per ogni intervallo mai passato dalla start_date a oggi — quasi
    mai quello che si vuole per una pipeline di manutenzione/batch come
    questa. Deve essere una scelta esplicita, non il default."""
    for dag_id, dag in dagbag.dags.items():
        assert dag.catchup is False, (
            f"DAG '{dag_id}' ha catchup={dag.catchup}: impostalo esplicitamente "
            f"a False a meno che il backfill sia voluto."
        )


def test_dags_have_tags(dagbag):
    """I tag sono l'unico modo per filtrare/raggruppare i DAG nella UI di
    Airflow quando il progetto ne avrà più di due."""
    for dag_id, dag in dagbag.dags.items():
        assert dag.tags, f"DAG '{dag_id}' non ha tag"
