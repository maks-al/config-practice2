"""Сохранение графа зависимостей в SVG"""

import re
from collections import deque
from pathlib import Path
from xml.sax.saxutils import escape

BOX_H = 46
GAP_Y = 24
GAP_X = 110
PAD = 35
MAX_LABEL = 65
BG = "#f7f9fc"
LINE = "#8293aa"
TEXT = "#14243b"
BLUE = "#2756a5"


def nodes_of(graph):
    """Собрать узлы в порядке появления"""
    return list(dict.fromkeys(
        list(graph) + [dep for deps in graph.values() for dep in deps]
    ))


def depths_of(graph, nodes):
    """Найти уровни узлов без рекурсии"""
    depth = {}
    for start in nodes:
        if start in depth:
            continue
        depth[start] = 0
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for child in graph.get(node, []):
                if child not in depth:
                    depth[child] = depth[node] + 1
                    queue.append(child)
    return depth


def layout(graph):
    """Разместить пакеты по уровням слева направо"""
    nodes = nodes_of(graph)
    depth = depths_of(graph, nodes)
    longest = max((len(name) for name in nodes), default=0)
    box_w = max(200, min(700, longest * 9 + 30))
    levels = {}
    for name in nodes:
        levels.setdefault(depth[name], []).append(name)
    pos = {}
    for level, names in levels.items():
        for index, name in enumerate(names):
            x = PAD + level * (box_w + GAP_X)
            y = PAD + index * (BOX_H + GAP_Y)
            pos[name] = (x, y)
    width = 2 * PAD + max(1, len(levels)) * (box_w + GAP_X)
    height = 2 * PAD + max((len(v) for v in levels.values()), default=1) * (
        BOX_H + GAP_Y
    )
    return pos, box_w, width, height


def edge_lines(graph, pos, box_w):
    """Подготовить направленные связи между прямоугольниками"""
    lines = []
    for name, deps in graph.items():
        x1, y1 = pos[name]
        for dep in dict.fromkeys(deps):
            x2, y2 = pos[dep]
            if name == dep:
                x = x1 + box_w / 2
                y = y1 + BOX_H
                path = f"M{x} {y} q0 40 25 25 q25 -15 0 -25"
                lines.append(f'<path d="{path}" marker-end="url(#arrow)"/>')
                continue
            start = (x1 + box_w, y1 + BOX_H / 2)
            end = (x2, y2 + BOX_H / 2)
            if x2 <= x1:
                start = (x1 + box_w / 2, y1 + BOX_H)
                end = (x2 + box_w / 2, y2)
            lines.append(
                f'<line x1="{start[0]}" y1="{start[1]}" '
                f'x2="{end[0]}" y2="{end[1]}" '
                f'marker-end="url(#arrow)"/>'
            )
    return lines


def node_lines(pos, box_w, root):
    """Подготовить прямоугольники с подписями пакетов"""
    lines = []
    for name, (x, y) in pos.items():
        fill = BLUE if name == root else "#ffffff"
        color = "#ffffff" if name == root else TEXT
        label = escape(name[:MAX_LABEL])
        title = escape(name)
        lines.append(f'<g><title>{title}</title>')
        lines.append(
            f'<rect x="{x}" y="{y}" width="{box_w}" '
            f'height="{BOX_H}" rx="8" fill="{fill}" stroke="{BLUE}"/>'
        )
        lines.append(
            f'<text x="{x + 12}" y="{y + 29}" fill="{color}">'
            f'{label}</text></g>'
        )
    return lines


def save_svg(graph, root, folder):
    """Сохранить SVG в папку output"""
    output = Path(folder)
    output.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", root)[:80]
    file = output / f"{name.strip('.') or 'graph'}.svg"
    pos, box_w, width, height = layout(graph)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="{BG}"/>',
        f'<defs><marker id="arrow" markerWidth="10" markerHeight="7" '
        f'refX="9" refY="3.5" orient="auto">'
        f'<path d="M0 0 L10 3.5 L0 7 Z" fill="{LINE}"/>'
        f'</marker></defs>',
        f'<g stroke="{LINE}" stroke-width="2" fill="none">',
        *edge_lines(graph, pos, box_w),
        '</g>',
        '<g font-family="Segoe UI, Arial, sans-serif" font-size="15">',
        *node_lines(pos, box_w, root),
        '</g>',
        '</svg>',
    ]
    file.write_text("\n".join(lines), encoding="utf-8")
    return file
