"""Tests del panel. El más importante: project.yml no puede "mentir" sobre el estado del repo."""

import pytest

from panel.diagram import build_dot
from panel.meta import MetaError, load_meta, missing_ready_paths, parse_meta, repo_root


@pytest.fixture(scope="module")
def meta():
    return load_meta()


def test_project_yml_es_valido(meta) -> None:
    assert len(meta.stages) == 9
    assert meta.nodes, "el mapa no puede estar vacío"


def test_todo_lo_listo_existe_en_el_repo(meta) -> None:
    # Si marcás algo como "listo" y no existe (o lo borraste), este test falla.
    assert missing_ready_paths(meta, repo_root()) == []


def test_progreso_entre_0_y_1(meta) -> None:
    assert 0.0 <= meta.progress() <= 1.0


def test_diagrama_incluye_todos_los_nodos(meta) -> None:
    dot = build_dot(meta.arch_nodes, meta.arch_edges)
    assert dot.startswith("digraph")
    assert dot.count("{") == dot.count("}")
    for node in meta.arch_nodes:
        assert f'"{node.id}"' in dot


MINIMO = {
    "stages": [{"number": 1, "name": "Base", "status": "listo"}],
    "map": [{"path": "README.md", "stage": 1, "status": "listo", "description": "x"}],
    "architecture": {"nodes": [], "edges": []},
}


def test_estado_invalido_da_error_claro() -> None:
    raw = {**MINIMO, "map": [{**MINIMO["map"][0], "status": "terminado"}]}
    with pytest.raises(MetaError, match="terminado"):
        parse_meta(raw)


def test_flecha_a_nodo_inexistente() -> None:
    raw = {**MINIMO, "architecture": {"nodes": [], "edges": [{"from": "a", "to": "b"}]}}
    with pytest.raises(MetaError, match="inexistente"):
        parse_meta(raw)


def test_alinear_con_nodo_inexistente() -> None:
    nodo = {"id": "airflow", "label": "A", "stage": 1, "status": "listo", "align_with": "nada"}
    raw = {**MINIMO, "architecture": {"nodes": [nodo], "edges": []}}
    with pytest.raises(MetaError, match="nada"):
        parse_meta(raw)


def test_etapa_inexistente() -> None:
    raw = {**MINIMO, "map": [{**MINIMO["map"][0], "stage": 99}]}
    with pytest.raises(MetaError, match="99"):
        parse_meta(raw)
