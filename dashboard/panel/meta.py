"""Lee y valida dashboard/project.yml, la fuente de verdad del panel."""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

Status = Literal["pendiente", "en_construccion", "listo"]
STATUSES: tuple[Status, ...] = ("pendiente", "en_construccion", "listo")
STATUS_ICON: dict[str, str] = {"pendiente": "⚪", "en_construccion": "🟡", "listo": "🟢"}
STATUS_LABEL: dict[str, str] = {
    "pendiente": "Pendiente",
    "en_construccion": "En construcción",
    "listo": "Listo",
}
SUGGESTION_STATUSES = ("pendiente", "hecha", "descartada")
EDGE_KINDS = ("data", "control")

DEFAULT_META_PATH = Path(__file__).resolve().parents[1] / "project.yml"


class MetaError(ValueError):
    """project.yml tiene un error de contenido (estado inválido, referencia rota, etc.)."""


@dataclass(frozen=True)
class Stage:
    number: int
    name: str
    status: Status


@dataclass(frozen=True)
class MapNode:
    path: str
    description: str
    stage: int
    status: Status

    @property
    def is_dir(self) -> bool:
        return self.path.endswith("/")

    @property
    def depth(self) -> int:
        return self.path.rstrip("/").count("/")

    @property
    def name(self) -> str:
        base = self.path.rstrip("/").rsplit("/", 1)[-1]
        return f"{base}/" if self.is_dir else base


@dataclass(frozen=True)
class ArchNode:
    id: str
    label: str
    detail: str
    stage: int
    status: Status
    # Se dibuja en la misma fila que este nodo (p. ej. Calidad al lado de Silver, que valida).
    align_with: str | None = None


@dataclass(frozen=True)
class ArchEdge:
    src: str
    dst: str
    kind: str


@dataclass(frozen=True)
class DiaryEntry:
    stage: int
    date: str
    title: str
    built: tuple[str, ...]
    decisions: tuple[str, ...]
    learned: tuple[str, ...]


@dataclass(frozen=True)
class Suggestion:
    title: str
    stage: int
    effort: str
    benefit: str
    status: str


@dataclass(frozen=True)
class ProjectMeta:
    stages: tuple[Stage, ...]
    nodes: tuple[MapNode, ...]
    arch_nodes: tuple[ArchNode, ...]
    arch_edges: tuple[ArchEdge, ...]
    diary: tuple[DiaryEntry, ...]
    suggestions: tuple[Suggestion, ...]

    def stage(self, number: int) -> Stage:
        return next(s for s in self.stages if s.number == number)

    def status_counts(self) -> dict[str, int]:
        counts = Counter(n.status for n in self.nodes)
        return {s: counts.get(s, 0) for s in STATUSES}

    def progress(self) -> float:
        """Avance del mapa: listo cuenta 1, en construcción 0.5, pendiente 0."""
        if not self.nodes:
            return 0.0
        weights = {"listo": 1.0, "en_construccion": 0.5, "pendiente": 0.0}
        return sum(weights[n.status] for n in self.nodes) / len(self.nodes)


def repo_root() -> Path:
    """Raíz del repo. En Docker se monta en /repo (variable REPO_ROOT)."""
    env = os.getenv("REPO_ROOT")
    return Path(env) if env else Path(__file__).resolve().parents[2]


def _status(value: Any, where: str) -> Status:
    if value not in STATUSES:
        raise MetaError(f"{where}: estado {value!r} inválido. Válidos: {', '.join(STATUSES)}")
    return cast(Status, value)


def _strs(values: Any) -> tuple[str, ...]:
    return tuple(str(v) for v in (values or []))


def parse_meta(raw: dict[str, Any]) -> ProjectMeta:
    """Convierte el YAML crudo en objetos tipados y valida que sea coherente."""
    try:
        stages = tuple(
            Stage(int(s["number"]), str(s["name"]), _status(s["status"], f"etapa {s['number']}"))
            for s in raw["stages"]
        )
        known_stages = {s.number for s in stages}

        def _stage(value: Any, where: str) -> int:
            if value not in known_stages:
                raise MetaError(f"{where}: la etapa {value!r} no existe en «stages»")
            return int(value)

        nodes = tuple(
            MapNode(
                path=str(n["path"]),
                description=str(n["description"]),
                stage=_stage(n["stage"], n["path"]),
                status=_status(n["status"], n["path"]),
            )
            for n in raw["map"]
        )
        arch = raw["architecture"]
        arch_nodes = tuple(
            ArchNode(
                id=str(n["id"]),
                label=str(n["label"]),
                detail=str(n.get("detail", "")),
                stage=_stage(n["stage"], f"nodo {n['id']}"),
                status=_status(n["status"], f"nodo {n['id']}"),
                align_with=n.get("align_with"),
            )
            for n in arch["nodes"]
        )
        arch_edges = tuple(
            ArchEdge(str(e["from"]), str(e["to"]), str(e.get("kind", "data")))
            for e in arch["edges"]
        )
        diary = tuple(
            DiaryEntry(
                stage=_stage(d["stage"], f"diario «{d['title']}»"),
                date=str(d["date"]),
                title=str(d["title"]),
                built=_strs(d.get("built")),
                decisions=_strs(d.get("decisions")),
                learned=_strs(d.get("learned")),
            )
            for d in raw.get("diary", [])
        )
        suggestions = tuple(
            Suggestion(
                title=str(s["title"]),
                stage=_stage(s["stage"], f"sugerencia «{s['title']}»"),
                effort=str(s["effort"]),
                benefit=str(s["benefit"]),
                status=str(s["status"]),
            )
            for s in raw.get("suggestions", [])
        )
    except KeyError as exc:
        raise MetaError(f"Falta el campo {exc} en project.yml") from exc

    duplicated = [p for p, c in Counter(n.path for n in nodes).items() if c > 1]
    if duplicated:
        raise MetaError(f"Rutas repetidas en el mapa: {duplicated}")

    ids = {n.id for n in arch_nodes}
    for n in arch_nodes:
        if n.align_with and n.align_with not in ids:
            raise MetaError(f"El nodo {n.id} se alinea con {n.align_with!r}, que no existe")
    for e in arch_edges:
        if e.src not in ids or e.dst not in ids:
            raise MetaError(f"La flecha {e.src} → {e.dst} apunta a un nodo inexistente")
        if e.kind not in EDGE_KINDS:
            raise MetaError(f"La flecha {e.src} → {e.dst} tiene tipo inválido {e.kind!r}")

    for s in suggestions:
        if s.status not in SUGGESTION_STATUSES:
            raise MetaError(f"Sugerencia «{s.title}»: estado {s.status!r} inválido")

    return ProjectMeta(stages, nodes, arch_nodes, arch_edges, diary, suggestions)


def load_meta(path: Path = DEFAULT_META_PATH) -> ProjectMeta:
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)  # safe_load: nunca ejecuta código embebido en el YAML
    if not isinstance(raw, dict):
        raise MetaError(f"{path} está vacío o no es un diccionario YAML")
    return parse_meta(raw)


def missing_ready_paths(meta: ProjectMeta, root: Path) -> list[str]:
    """Rutas marcadas «listo» que no existen en disco: señal de que project.yml quedó desfasado."""
    return [n.path for n in meta.nodes if n.status == "listo" and not (root / n.path).exists()]
