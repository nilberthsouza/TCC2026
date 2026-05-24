"""
topology_utils.py
-----------------
Funções utilitárias de topologia de rede:
  - construção de grafos (NetworkX e adjacência própria)
  - cálculo de caminhos e distâncias
  - comprimento do alimentador
  - impedâncias de sequência ao longo de um caminho
"""

import networkx as nx
from collections import defaultdict, deque


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _norm_bus(bus: str) -> str:
    """Normaliza nome de barra: minúsculo e sem sufixo 'r' (ex: 814r -> 814)."""
    return bus.split(".")[0].lower().rstrip("r")


# ─────────────────────────────────────────────────────────────────────────────
# Grafo NetworkX — leitura direta do arquivo DSS
# ─────────────────────────────────────────────────────────────────────────────

def build_networkx_graph(dss_file: str) -> nx.Graph:
    """
    Constrói grafo NetworkX lendo o arquivo DSS diretamente.
    Ignora linhas comentadas (!). Retorna grafo com edge weight = comprimento [mi].
    """
    def clean_bus(b: str) -> str:
        return b.split(".")[0].lower().rstrip("r")

    G = nx.Graph()
    with open(dss_file, encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("!"):
                continue
            low = line.lower()
            if not low.startswith("new line."):
                continue
            bus1 = bus2 = ""
            length = 0.0
            for token in line.split():
                tl = token.lower()
                if tl.startswith("bus1="):
                    bus1 = clean_bus(token.split("=", 1)[1])
                elif tl.startswith("bus2="):
                    bus2 = clean_bus(token.split("=", 1)[1])
                elif tl.startswith("length="):
                    try:
                        length = float(token.split("=", 1)[1])
                    except ValueError:
                        pass
            if bus1 and bus2:
                G.add_edge(bus1, bus2, weight=length)
    return G


def calc_ref_distances(G: nx.Graph, relay_bus: str,
                       fault_buses: list[str]) -> dict[str, float]:
    """
    Calcula distâncias (shortest path por peso) de relay_bus até cada
    barra em fault_buses. Retorna dict {barra: distancia_mi}.
    """
    origin = _norm_bus(relay_bus)
    result = {}
    for fb in fault_buses:
        dest = _norm_bus(fb)
        try:
            d = nx.shortest_path_length(G, source=origin, target=dest, weight="weight")
            result[fb] = round(d, 4)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            result[fb] = float("nan")
    return result


def calc_feeder_length(relay_bus: str, G: nx.Graph) -> float:
    """
    Comprimento do alimentador = distância do relay_bus até a barra
    mais distante no subgrafo downstream (via Dijkstra ponderado).
    """
    origin = _norm_bus(relay_bus)
    try:
        lengths = nx.single_source_dijkstra_path_length(G, origin, weight="weight")
        return round(max(lengths.values()), 4)
    except Exception:
        return 0.0


def calc_feeder_farthest_bus(relay_bus: str, G: nx.Graph) -> str:
    """
    Retorna o nome da barra mais distante de relay_bus (em comprimento).
    Usado para determinar o destino do caminho completo do alimentador.
    """
    origin = _norm_bus(relay_bus)
    try:
        lengths = nx.single_source_dijkstra_path_length(G, origin, weight="weight")
        return max(lengths, key=lengths.get)
    except Exception:
        return origin


# ─────────────────────────────────────────────────────────────────────────────
# Grafo de adjacência próprio — via API OpenDSS
# ─────────────────────────────────────────────────────────────────────────────

def build_network_graph(dss) -> dict[str, list[tuple]]:
    """
    Constrói grafo de adjacência da rede lendo todos os elementos Line.
    Retorna: {bus: [(vizinho, line_name, length_mi, r1, x1, r0, x0), ...]}
    """
    graph = defaultdict(list)
    flag  = dss.lines.first()
    while flag > 0:
        name = dss.lines.name
        dss.circuit.set_active_element(f"Line.{name}")
        b1   = _norm_bus(dss.cktelement.bus_names[0])
        b2   = _norm_bus(dss.cktelement.bus_names[1])
        dss.lines.name = name
        length = dss.lines.length
        r1     = dss.lines.r1
        x1     = dss.lines.x1
        r0     = dss.lines.r0
        x0     = dss.lines.x0
        graph[b1].append((b2, name, length, r1, x1, r0, x0))
        graph[b2].append((b1, name, length, r1, x1, r0, x0))
        flag = dss.lines.next()
    return graph


def find_shortest_path(graph: dict, start: str, end: str) -> list[tuple]:
    """
    BFS: caminho de menor número de saltos entre start e end.
    Retorna lista de segmentos: [(line_name, b_from, b_to, length, r1, x1, r0, x0), ...]
    """
    start = _norm_bus(start)
    end   = _norm_bus(end)
    visited = {start}
    queue   = deque([(start, [])])
    while queue:
        node, path = queue.popleft()
        if node == end:
            return path
        for (nb, name, length, r1, x1, r0, x0) in graph[node]:
            if nb not in visited:
                visited.add(nb)
                seg = (name, node, nb, length, r1, x1, r0, x0)
                queue.append((nb, path + [seg]))
    return []


def path_sequence_impedances(path: list[tuple]) -> tuple[complex, complex, float]:
    """
    Soma as impedâncias de sequência de cada segmento do caminho.

    Usa as impedâncias reais de cada segmento lidas do OpenDSS
    (r1, x1, r0, x0 por milha × comprimento do segmento).

    Retorna (Z1_total [Ohm], Z0_total [Ohm], L_total [mi]).
    O resultado é impedância PURA — Takagi divide num/den e obtém d_pu [adimensional],
    que deve ser multiplicado por L_alimentador para obter d_mi.
    """
    Z1_total = 0 + 0j
    Z0_total = 0 + 0j
    L_total  = 0.0
    for (name, b1, b2, length, r1, x1, r0, x0) in path:
        Z1_total += complex(r1, x1) * length
        Z0_total += complex(r0, x0) * length
        L_total  += length
    return Z1_total, Z0_total, L_total


def find_feeder_path(graph: dict, relay_bus: str,
                     farthest_bus: str) -> list[tuple]:
    """
    Retorna o caminho completo relay_bus -> farthest_bus usando BFS.
    Usado para calcular Z1L e Z0L do alimentador inteiro (sem conhecer a falta).
    """
    return find_shortest_path(graph, relay_bus, farthest_bus)


# ─────────────────────────────────────────────────────────────────────────────
# Multi-folha: folhas, distâncias acumuladas, barra mais próxima
# ─────────────────────────────────────────────────────────────────────────────

def find_leaves(graph: dict, relay_bus: str) -> list[str]:
    """
    Retorna todas as barras folha do grafo (grau 1), excluindo relay_bus.
    Uma barra folha tem apenas uma conexão — é terminal de ramal.
    """
    relay = _norm_bus(relay_bus)
    return [bus for bus, neighbors in graph.items()
            if len(neighbors) == 1 and bus != relay]


def get_all_distances_from_relay(graph: dict, relay_bus: str) -> dict[str, float]:
    """
    BFS ponderado a partir de relay_bus.
    Retorna {barra: distancia_acumulada_mi} para todas as barras alcançáveis.
    """
    origin = _norm_bus(relay_bus)
    distances = {origin: 0.0}
    queue = deque([(origin, 0.0)])
    while queue:
        node, dist_so_far = queue.popleft()
        for (nb, name, length, r1, x1, r0, x0) in graph[node]:
            if nb not in distances:
                new_dist = dist_so_far + length
                distances[nb] = new_dist
                queue.append((nb, new_dist))
    return distances


def find_nearest_bus(distances_from_relay: dict[str, float],
                     d_mi: float,
                     path: list[tuple]) -> str:
    """
    Dado d_mi estimado pelo Takagi e o caminho relay → folha,
    retorna a barra do caminho cuja distância acumulada ao relay
    é mais próxima de d_mi (por valor absoluto).
    """
    best_bus  = None
    best_diff = float("inf")
    for (name, b_from, b_to, length, r1, x1, r0, x0) in path:
        for bus in (b_from, b_to):
            dist = distances_from_relay.get(bus, float("inf"))
            diff = abs(dist - d_mi)
            if diff < best_diff:
                best_diff = diff
                best_bus  = bus
    return best_bus


def build_leaves_cache(graph: dict, relay_bus: str,
                       leaves: list[str]) -> dict[str, tuple]:
    """
    Para cada folha calcula e armazena (path, Z1L, Z0L, L_folha).
    Retorna dict {folha: (path, Z1L, Z0L, L_folha)}.
    """
    cache = {}
    for leaf in leaves:
        path = find_shortest_path(graph, relay_bus, leaf)
        if path:
            Z1L, Z0L, L = path_sequence_impedances(path)
            cache[leaf] = (path, Z1L, Z0L, L)
    return cache


def find_relay_line(dss, relay_bus: str) -> str:
    """
    Encontra automaticamente a linha do relay: aquela cujo bus2
    (terminal 2) é a barra do relay. Isso garante que o terminal 1
    aponta para a fonte, preservando o sentido correto da corrente.

    Retorna a string no formato 'Line.<nome>' pronta para uso.
    Levanta ValueError se nenhuma linha for encontrada.
    """
    target = _norm_bus(relay_bus)
    flag   = dss.lines.first()
    while flag > 0:
        name = dss.lines.name
        dss.circuit.set_active_element(f"Line.{name}")
        b2 = _norm_bus(dss.cktelement.bus_names[1])
        if b2 == target:
            return f"Line.{name}"
        flag = dss.lines.next()
    raise ValueError(
        f"Nenhuma linha encontrada com bus2={relay_bus}. "
        f"Verifique se RELAY_BUS está correto."
    )