import py_dss_interface
import numpy as np
from collections import defaultdict, deque

dss = py_dss_interface.DSS()

# =====================================================
# CONFIGURAÇÕES
# =====================================================
DSS_FILE    = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal14mi.dss"
RELAY_BUS   = "812"
RELAY_LINE  = "Line.L5"      # linha que o relay monitora (terminal 1 = barra relay)
FAULT_BUSES = ["850", "854", "822", "834", "840", "848"]
REF_LINECODE = "301"         # linecode de referência para impedâncias por milha
Sbase_MVA   = 40.0
Sbase       = Sbase_MVA * 1e6

# Operador de Fortescue e sua inversa
_a   = np.exp(1j * 2 * np.pi / 3)
A    = np.array([[1,    1,      1    ],
                 [1,    _a**2,  _a   ],
                 [1,    _a,     _a**2]], dtype=complex)
Ainv = np.linalg.inv(A)


# =====================================================
# FUNÇÕES UTILITÁRIAS — CIRCUITO
# =====================================================

def compile_circuit(add_meter: bool = False) -> None:
    """Recompila o circuito base e opcionalmente adiciona EnergyMeter."""
    dss.text(f"compile {DSS_FILE}")
    if add_meter:
        dss.text(f"New EnergyMeter.M1 Element={RELAY_LINE} Terminal=1")
    dss.solution.solve()


def polar_to_rect(mag: float, ang_deg: float) -> complex:
    """Magnitude + angulo (graus) -> numero complexo."""
    ang = np.deg2rad(ang_deg)
    return mag * (np.cos(ang) + 1j * np.sin(ang))


def get_bus_voltages(bus: str, n_phases: int = 3) -> np.ndarray:
    """Array complexo (n_phases,) das tensoes de fase na barra."""
    dss.circuit.set_active_bus(bus)
    v = dss.bus.vmag_angle
    return np.array([polar_to_rect(v[2*k], v[2*k+1]) for k in range(n_phases)],
                    dtype=complex)


def get_line_currents(element: str, terminal: int = 1, n_phases: int = 3) -> np.ndarray:
    """
    Array complexo (n_phases,) das correntes no terminal indicado.
    terminal=1 -> offset 0 (relay side, sentido fisico correto).
    terminal=2 -> offset n_phases*2 (EVITAR: aparece defasado ~180 graus).
    """
    dss.circuit.set_active_element(element)
    curr   = dss.cktelement.currents_mag_ang
    offset = (terminal - 1) * 2 * n_phases
    return np.array([polar_to_rect(curr[offset + 2*k], curr[offset + 2*k+1])
                     for k in range(n_phases)], dtype=complex)


def compute_bases(bus: str) -> tuple[float, float, float, float]:
    """
    Bases do sistema na barra informada.
    Retorna (Vbase_ln [V], Vbase_ll [V], Ibase [A], Zbase [Ohm]).
    """
    dss.circuit.set_active_bus(bus)
    Vln   = dss.bus.kv_base * 1e3
    Vll   = Vln * np.sqrt(3)
    Ibase = Sbase / (np.sqrt(3) * Vll)
    Zbase = Vll**2 / Sbase
    return Vln, Vll, Ibase, Zbase


def get_thevenin_seq_impedances(bus: str) -> tuple[complex, complex]:
    """
    Z0eq e Z1eq de Thevenin na barra via Zbus = pinv(Ybus).
    Retorna (Z0eq, Z1eq) em Ohm.
    """
    y_flat = dss.circuit.system_y
    y_cplx = np.array(y_flat[0::2]) + 1j * np.array(y_flat[1::2])
    n      = int(np.sqrt(len(y_cplx)))
    Ybus   = y_cplx.reshape((n, n))
    Zbus   = np.linalg.pinv(Ybus)
    nodes  = dss.circuit.y_node_order
    idx    = [nodes.index(f"{bus}.1"),
              nodes.index(f"{bus}.2"),
              nodes.index(f"{bus}.3")]
    Zabc   = Zbus[np.ix_(idx, idx)]
    Z012   = Ainv @ Zabc @ A
    return Z012[0, 0], Z012[1, 1]


# =====================================================
# FUNÇÕES UTILITÁRIAS — LINECODE DE REFERÊNCIA
# =====================================================

def get_linecode_params(linecode_name: str) -> tuple[float, float, float, float]:
    """
    Lê r1, x1, r0, x0 (Ohm/mi) do linecode informado.
    Retorna (r1, x1, r0, x0).
    """
    dss.text(f"select linecode.{linecode_name}")
    r1 = dss.linecodes.r1
    x1 = dss.linecodes.x1
    r0 = dss.linecodes.r0
    x0 = dss.linecodes.x0
    return r1, x1, r0, x0


# =====================================================
# FUNCOES UTILITARIAS — TOPOLOGIA
# =====================================================

def _norm_bus(bus: str) -> str:
    """Normaliza nome de barra: minusculo e sem sufixo 'r' (ex: 814r -> 814)."""
    return bus.split(".")[0].lower().rstrip("r")


def build_network_graph() -> dict[str, list[tuple]]:
    """
    Constroi grafo de adjacencia da rede lendo todos os elementos Line.
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
        entry  = (b2, name, length, r1, x1, r0, x0)
        graph[b1].append(entry)
        graph[b2].append((b1, name, length, r1, x1, r0, x0))
        flag = dss.lines.next()
    return graph


def find_shortest_path(graph: dict, start: str, end: str) -> list[tuple]:
    """
    BFS: caminho de menor numero de saltos entre start e end.
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


def path_sequence_impedances(path: list[tuple],
                             r1_ref: float, x1_ref: float,
                             r0_ref: float, x0_ref: float) -> tuple[complex, complex, float]:
    """
    Calcula Z1 e Z0 totais do caminho usando impedâncias por milha do
    linecode de referência (REF_LINECODE) em vez dos parâmetros reais
    de cada segmento. O comprimento real de cada segmento é preservado.

    Isso é consistente com o algoritmo de Takagi: o localizador não
    conhece a priori onde ocorreu a falta, portanto usa um único modelo
    homogêneo de linha para todo o alimentador.

    Retorna (Z1_total [Ohm], Z0_total [Ohm], L_total [mi]).
    """
    Z1_ref   = complex(r1_ref, x1_ref)   # Ohm/mi — fixo, do linecode de referência
    Z0_ref   = complex(r0_ref, x0_ref)   # Ohm/mi — fixo, do linecode de referência
    L_total  = sum(seg[3] for seg in path)
    Z1_total = Z1_ref * L_total
    Z0_total = Z0_ref * L_total
    return Z1_total, Z0_total, L_total


# =====================================================
# LOCALIZADOR DE TAKAGI MODIFICADO
# =====================================================

def takagi_3ph(Va: complex, Ia: complex, Ia_pre: complex,
               Z1L: complex, L_mi: float) -> float | None:
    """
    Takagi classico para falta TRIFASICA.
      d = Im(Va * dIa*) / Im(Z1L * Ia * dIa*)
    Z1L = impedancia de seq. positiva TOTAL do caminho [Ohm].
    Retorna d em milhas.
    """
    dIa     = Ia - Ia_pre
    dIa_c   = np.conj(dIa)
    num     = np.imag(Va * dIa_c)
    den     = np.imag(Z1L * Ia * dIa_c)
    if np.isclose(den, 0.0):
        return None
    return (num / den) * L_mi


def takagi_1ph(Va: complex, Iabc: np.ndarray, Iabc_pre: np.ndarray,
               Z1L: complex, Z0L: complex, L_mi: float) -> float | None:
    """
    Takagi MODIFICADO para falta MONOFASICA (1F-T), com compensacao
    de sequencia zero via fator k0.

    Formulacao:
      k0     = (Z0L - Z1L) / (3 * Z1L)          fator de compensacao
      I3I0   = Ia + Ib + Ic                       3 * I0 (soma das fases)
      Icomp  = Ia + k0 * I3I0                    corrente compensada
      d_pu   = Im(Va * dIcomp*) / Im(Z1L * Icomp * dIcomp*)
      d_mi   = d_pu * L_mi
    """
    k0       = (Z0L - Z1L) / (3.0 * Z1L)
    I3I0     = Iabc[0] + Iabc[1] + Iabc[2]
    Icomp    = Iabc[0] + k0 * I3I0

    I3I0_pre = Iabc_pre[0] + Iabc_pre[1] + Iabc_pre[2]
    Icomp_pre= Iabc_pre[0] + k0 * I3I0_pre

    dIcomp   = Icomp - Icomp_pre
    dIcomp_c = np.conj(dIcomp)

    num = np.imag(Va * dIcomp_c)
    den = np.imag(Z1L * Icomp * dIcomp_c)
    if np.isclose(den, 0.0):
        return None
    return (num / den) * L_mi


# =====================================================
# HELPERS DE IMPRESSAO
# =====================================================
W = 72

def section(title: str) -> None:
    print(f"\n{'=' * W}")
    print(f"  {title}")
    print(f"{'=' * W}")


def fmt(val: complex, base: float, unit: str) -> str:
    mag    = abs(val)
    ang    = np.degrees(np.angle(val))
    mag_pu = mag / base
    return (f"{mag:>12.4f} {unit} angle {ang:>+7.2f} deg  "
            f"({val.real:>+10.4f}{val.imag:>+10.4f}j)  "
            f"-> {mag_pu:.6f} pu")


def pline(label: str, val: complex, base: float, unit: str) -> None:
    print(f"  {label:<20} {fmt(val, base, unit)}")


# =====================================================
# ETAPA 1 — BASES DO SISTEMA
# =====================================================
compile_circuit()
Vln, Vll, Ibase, Zbase = compute_bases(RELAY_BUS)

section("BASES DO SISTEMA")
print(f"  Relay bus          : {RELAY_BUS}")
print(f"  Linha monitorada   : {RELAY_LINE}")
print(f"  Vbase fase-neutro  : {Vln:.2f} V")
print(f"  Vbase fase-fase    : {Vll:.2f} V")
print(f"  Sbase              : {Sbase_MVA:.1f} MVA")
print(f"  Ibase              : {Ibase:.4f} A")
print(f"  Zbase              : {Zbase:.6f} Ohm")

# =====================================================
# ETAPA 1b — PARÂMETROS DO LINECODE DE REFERÊNCIA
# =====================================================
r1_ref, x1_ref, r0_ref, x0_ref = get_linecode_params(REF_LINECODE)
Z1_ref_per_mi = complex(r1_ref, x1_ref)
Z0_ref_per_mi = complex(r0_ref, x0_ref)

section(f"LINECODE DE REFERÊNCIA  —  {REF_LINECODE}")
print(f"  r1  : {r1_ref:.6f} Ohm/mi")
print(f"  x1  : {x1_ref:.6f} Ohm/mi")
print(f"  r0  : {r0_ref:.6f} Ohm/mi")
print(f"  x0  : {x0_ref:.6f} Ohm/mi")
print(f"  |Z1|: {abs(Z1_ref_per_mi):.6f} Ohm/mi")
print(f"  |Z0|: {abs(Z0_ref_per_mi):.6f} Ohm/mi")

# =====================================================
# ETAPA 2 — CONDICOES PRE-FALTA
# =====================================================
V_pre    = get_bus_voltages(RELAY_BUS)
Iabc_pre = get_line_currents(RELAY_LINE)    # (3,) [A] — terminal 1, sentido relay->rede

section("CONDICOES PRE-FALTA  —  barra relay  (fase A)")
pline("Tensao Va_pre",    V_pre[0],    Vln,   "V")
pline("Corrente Ia_pre",  Iabc_pre[0], Ibase, "A")

# =====================================================
# ETAPA 3 — CURTO TRIFASICO NA BARRA DO RELAY
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F3F Bus1={RELAY_BUS} Phases=3 R=0.0001")
dss.solution.solve()

I_3F = get_line_currents(RELAY_LINE)

section("CURTO TRIFASICO (3F)  —  barra relay  (fase A)")
pline("Icc3F", I_3F[0], Ibase, "A")

# =====================================================
# ETAPA 4 — CURTO MONOFASICO NA BARRA DO RELAY (A-terra)
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F1F Bus1={RELAY_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

I_1F = get_line_currents(RELAY_LINE)

section("CURTO MONOFASICO 1F-T  —  barra relay  (fase A)")
pline("Icc1F", I_1F[0], Ibase, "A")

# =====================================================
# ETAPA 5 — IMPEDANCIAS DE THEVENIN (Z0eq, Z1eq)
# =====================================================
compile_circuit(add_meter=True)
Z0eq, Z1eq = get_thevenin_seq_impedances(RELAY_BUS)

section("IMPEDANCIAS DE THEVENIN  —  barra relay")
for label, Z in (("Z0eq", Z0eq), ("Z1eq", Z1eq)):
    Zpu = Z / Zbase
    print(f"  {label}  :  {Z.real:>+10.6f} {Z.imag:>+10.6f}j Ohm"
          f"  |  |Z| = {abs(Z):>10.6f} Ohm"
          f"  ->  {Zpu.real:>+10.6f} {Zpu.imag:>+10.6f}j pu"
          f"  |  |Z| = {abs(Zpu):.6f} pu")

# =====================================================
# ETAPA 5b — VALIDAÇÃO THÉVENIN / MÉTODO DO ARTIGO
# =====================================================
compile_circuit(add_meter=True)

dss.circuit.set_active_element(RELAY_LINE)
pwr = dss.cktelement.powers
S_mag_kva = pwr[0]
S_ang_deg = pwr[1]
S_phA     = polar_to_rect(S_mag_kva, S_ang_deg)
P_phA     = S_phA.real
Q_phA     = S_phA.imag

pf_raw = P_phA / abs(S_phA) if not np.isclose(abs(S_phA), 0.0) else 1.0
pf     = float(np.clip(pf_raw, -1.0, 1.0))

theta_v_pre = np.angle(V_pre[0])
theta_i_pre = np.angle(Iabc_pre[0])

phi       = np.arccos(pf)
theta_vth = phi + theta_i_pre

Vth_mag = abs(V_pre[0])
Vth     = Vth_mag * np.exp(1j * theta_vth)
VLL_art = Vth_mag * np.sqrt(3)
k = Vth_mag / Vln

Icc3ph_mag = abs(I_3F[0])
Icc1ph_mag = abs(I_1F[0])

Z1eq_art_mag = (k * VLL_art) / (np.sqrt(3) * Icc3ph_mag)
Z0eq_art_mag = (np.sqrt(3) * k * VLL_art / Icc1ph_mag) - 2.0 * Z1eq_art_mag

ang_Z1_art = theta_vth - np.angle(I_3F[0])
ang_Z0_art = theta_vth - np.angle(I_1F[0])
Z1eq_art = Z1eq_art_mag * np.exp(1j * ang_Z1_art)
Z0eq_art = Z0eq_art_mag * np.exp(1j * ang_Z0_art)

def _pct_err(val: float, ref: float) -> float:
    return (val - ref) / ref * 100.0 if not np.isclose(ref, 0.0) else float("nan")

err_Z1_mag = _pct_err(abs(Z1eq_art), abs(Z1eq))
err_Z0_mag = _pct_err(abs(Z0eq_art), abs(Z0eq))
err_Z1_ang = np.degrees(ang_Z1_art) - np.degrees(np.angle(Z1eq))
err_Z0_ang = np.degrees(ang_Z0_art) - np.degrees(np.angle(Z0eq))

section("ETAPA 5b — VALIDAÇÃO THÉVENIN / MÉTODO DO ARTIGO")

print(f"\n  [ Potência pré-falta — terminal 1, fase A ]")
print(f"  P            : {P_phA:>+12.4f} kW")
print(f"  Q            : {Q_phA:>+12.4f} kvar")
print(f"  |S|          : {abs(S_phA):>12.4f} kVA")
print(f"  pf           : {pf:>12.6f}   (= cos {np.degrees(phi):>+.4f} deg)")

print(f"\n  [ Fasores angulares pré-falta — terminal 1 ]")
print(f"  theta_v_pre  : {np.degrees(theta_v_pre):>+12.4f} deg  (tensao fase A)")
print(f"  theta_i_pre  : {np.degrees(theta_i_pre):>+12.4f} deg  (corrente fase A, terminal 1)")
print(f"  phi = acos(pf): {np.degrees(phi):>+12.4f} deg")
print(f"  theta_vth    : {np.degrees(theta_vth):>+12.4f} deg  (= phi + theta_i_pre)")

print(f"\n  [ Tensão de Thévenin ]")
pline("Vth",  Vth, Vln, "V")
print(f"  VLL_art      : {VLL_art:>12.4f} V    (= |Vth| * sqrt(3))")
print(f"  k = |Vth|/Vln: {k:>12.6f} pu")

print(f"\n  [ Correntes de curto — terminal 1 ]")
pline("I_3F fase A",  I_3F[0], Ibase, "A")
pline("I_1F fase A",  I_1F[0], Ibase, "A")

print(f"\n  [ Impedâncias — comparação ]")
print(f"  {'':20} {'Artigo':>28}   {'Código (Zbus)':>28}   {'Erro |Z|':>9}  {'Erro ang':>9}")
print(f"  {'-' * 102}")

def _fmt_z(Z: complex, Zb: float) -> str:
    return (f"{abs(Z):>10.6f} Ohm  ∠{np.degrees(np.angle(Z)):>+8.3f}°"
            f"  ({abs(Z)/Zb:.6f} pu)")

print(f"  {'Z1eq':<20} {_fmt_z(Z1eq_art, Zbase)}   {_fmt_z(Z1eq, Zbase)}"
      f"   {err_Z1_mag:>+8.3f}%  {err_Z1_ang:>+8.3f}°")
print(f"  {'Z0eq':<20} {_fmt_z(Z0eq_art, Zbase)}   {_fmt_z(Z0eq, Zbase)}"
      f"   {err_Z0_mag:>+8.3f}%  {err_Z0_ang:>+8.3f}°")

# =====================================================
# ETAPA 6 — GRAFO DA REDE + CAMINHOS
# =====================================================
compile_circuit(add_meter=True)
graph = build_network_graph()

section("GRAFO DA REDE  —  caminhos relay -> barra de falta")
print(f"  Linecode de referência para Z: {REF_LINECODE}  "
      f"(|Z1|={abs(Z1_ref_per_mi):.4f} Ohm/mi, |Z0|={abs(Z0_ref_per_mi):.4f} Ohm/mi)")
print(f"  {'Barra':<8} {'L caminho (mi)':>15}  {'|Z1L| (Ohm)':>12}  {'|Z0L| (Ohm)':>12}  Segmentos")
print(f"  {'-' * W}")

paths_cache: dict[str, tuple] = {}
for fault_bus in FAULT_BUSES:
    path          = find_shortest_path(graph, RELAY_BUS, fault_bus)
    Z1L, Z0L, L  = path_sequence_impedances(path, r1_ref, x1_ref, r0_ref, x0_ref)
    paths_cache[fault_bus] = (path, Z1L, Z0L, L)
    segs = " -> ".join(f"[{s[0]}]({s[3]:.4f}mi)" for s in path)
    print(f"  {fault_bus:<8} {L:>15.4f}  {abs(Z1L):>12.6f}  {abs(Z0L):>12.6f}  {segs}")

# =====================================================
# ETAPA 7 — TAKAGI MODIFICADO PARA CADA BARRA DE FALTA
# =====================================================
section("LOCALIZADOR DE TAKAGI MODIFICADO  —  falta 1F-T fase A")
print(f"  {'Barra':<8} {'d (mi)':>10}  {'Ref (mi)':>10}  {'Erro (mi)':>10}  {'Erro (%)':>10}")
print(f"  {'-' * 56}")

REF = {"850": 0.620, "854": 2.180, "822": 3.000,
       "834": 4.050, "840": 6.750, "848": 7.470}

resultados: list[tuple] = []

for fault_bus in FAULT_BUSES:
    compile_circuit(add_meter=True)
    dss.text(f"New Fault.F1F Bus1={fault_bus}.1.0 Phases=1 R=0.0001")
    dss.solution.solve()

    V_fault        = get_bus_voltages(RELAY_BUS)
    Iabc_fault     = get_line_currents(RELAY_LINE, n_phases=3)   # terminal 1, relay->rede

    path, Z1L, Z0L, L = paths_cache[fault_bus]

    d_mi = takagi_1ph(
        Va       = V_fault[0],
        Iabc     = Iabc_fault,
        Iabc_pre = Iabc_pre,
        Z1L      = Z1L,
        Z0L      = Z0L,
        L_mi     = L,
    )

    Va_fault = V_fault[0]
    ref      = REF.get(fault_bus, float("nan"))
    if d_mi is not None:
        erro = d_mi - ref
        pct  = erro / 14 * 100
        print(f"  {fault_bus:<8} {d_mi:>10.4f}  {ref:>10.3f}  {erro:>+10.4f}  {pct:>+10.2f}%")
        resultados.append((fault_bus, d_mi, ref, Va_fault))
    else:
        print(f"  {fault_bus:<8} {'---':>10}  {ref:>10.3f}  denominador nulo")

# =====================================================
# RESUMO FINAL
# =====================================================
section("RESUMO")
print(f"  {'Barra':<8} {'d Takagi (mi)':>14}  {'Ref (mi)':>10}  {'Erro (mi)':>10}  {'Erro (%)':>10}"
      f"  {'|Va| (V)':>12}  {'Va (pu)':>10}  {'ang (deg)':>10}")
print(f"  {'-' * 96}")
for bus, d_mi, ref, Va in resultados:
    erro   = d_mi - ref
    pct    = erro / 14 * 100
    Va_mag = abs(Va)
    Va_pu  = Va_mag / Vln
    Va_ang = np.degrees(np.angle(Va))
    print(f"  {bus:<8} {d_mi:>14.4f}  {ref:>10.3f}  {erro:>+10.4f}  {pct:>+10.2f}%"
          f"  {Va_mag:>12.4f}  {Va_pu:>10.6f}  {Va_ang:>+10.2f}")

# =====================================================
# RESTAURA CIRCUITO ORIGINAL
# =====================================================
compile_circuit()