"""Genera el diagrama de arquitectura en lenguaje DOT (Graphviz).

Streamlit dibuja DOT directo en el navegador con st.graphviz_chart, sin instalar Graphviz.
"""

from __future__ import annotations

from panel.meta import ArchEdge, ArchNode

# (relleno, borde) por estado. Rellenos claros + texto oscuro: se lee bien en tema claro y oscuro.
COLORS: dict[str, tuple[str, str]] = {
    "listo": ("#d1fae5", "#047857"),
    "en_construccion": ("#fef3c7", "#b45309"),
    "pendiente": ("#f3f4f6", "#9ca3af"),
}


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def build_dot(nodes: tuple[ArchNode, ...], edges: tuple[ArchEdge, ...]) -> str:
    lines = [
        "digraph arquitectura {",
        # De arriba hacia abajo (TB): con 6 etapas en horizontal (LR) el diagrama queda tan ancho
        # que el navegador lo achica hasta que el texto no se lee.
        '  rankdir=TB; bgcolor="transparent"; nodesep=0.5; ranksep=0.45;',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=13,'
        ' fontcolor="#111827", margin="0.2,0.1", penwidth=1.6, width=2.2];',
        '  edge [color="#6b7280", arrowsize=0.7];',
    ]
    for n in nodes:
        fill, border = COLORS[n.status]
        # Lo pendiente va punteado: se ve "en borrador" hasta que lo construimos.
        style = "rounded,filled,dashed" if n.status == "pendiente" else "rounded,filled"
        label = _esc(n.label) + (f"\\n{_esc(n.detail)}" if n.detail else "")
        lines.append(
            f'  "{_esc(n.id)}" [label="{label}", fillcolor="{fill}", color="{border}",'
            f' style="{style}"];'
        )
    # Los nodos con align_with van en la misma fila que su par (p. ej. Calidad junto a Silver):
    # las flechas quedan cortas y no cruzan todo el diagrama.
    for n in nodes:
        if n.align_with:
            lines.append(f'  {{rank=same; "{_esc(n.align_with)}"; "{_esc(n.id)}";}}')
    for e in edges:
        attrs = ' [style=dashed, color="#8b5cf6"]' if e.kind == "control" else ""
        lines.append(f'  "{_esc(e.src)}" -> "{_esc(e.dst)}"{attrs};')
    lines.append("}")
    return "\n".join(lines)
