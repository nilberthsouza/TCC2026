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


# CORREÇÃO 1: default alterado de terminal=2 para terminal=1.
# No OpenDSS, currents_mag_ang retorna [T1_A_mag, T1_A_ang, T1_B_mag, T1_B_ang, ...,
#                                        T2_A_mag, T2_A_ang, ...].
# Terminal 1 -> offset 0 (primeiros n_phases pares).
# Terminal 2 -> offset n_phases*2 (segundos n_phases pares) — NUNCA usar aqui.
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
    Zbus   = np.linalg.pinv(Ybus)   #pode dar problema no alimentador real, tomar cuidado com o uso
    nodes  = dss.circuit.y_node_order
    idx    = [nodes.index(f"{bus}.1"),
              nodes.index(f"{bus}.2"),
              nodes.index(f"{bus}.3")]
    Zabc   = Zbus[np.ix_(idx, idx)]
    Z012   = Ainv @ Zabc @ A
    return Z012[0, 0], Z012[1, 1]


# =====================================================
# FUNCOES UTILITARIAS — TOPOLOGIA
# =====================================================


# fiz isso pra tratar problema com a distancia do alimentador, lembrar de verificar se ainda é necessario
def _norm_bus(bus: str) -> str:
    """Normaliza nome de barra: minusculo e sem sufixo 'r' (ex: 814r -> 814)."""
    return bus.split(".")[0].lower().rstrip("r")


# Não preciso mais disso, retirar
def build_network_graph() -> dict[str, list[tuple]]:
    """
    Constroi grafo de adjacencia da rede lendo todos os elementos Line.
    Usa first()/next() e set_active_element para leitura correta de r1/x1/r0/x0.
    Retorna: {bus: [(vizinho, line_name, length_mi, r1, x1, r0, x0), ...]}
    """
    graph = defaultdict(list)
    flag  = dss.lines.first()
    while flag > 0:
        name = dss.lines.name
        dss.circuit.set_active_element(f"Line.{name}")
        b1   = _norm_bus(dss.cktelement.bus_names[0])
        b2   = _norm_bus(dss.cktelement.bus_names[1])
        dss.lines.name = name          # restaura ponteiro
        length = dss.lines.length      # mi
        r1     = dss.lines.r1          # Ohm/mi seq positiva
        x1     = dss.lines.x1
        r0     = dss.lines.r0          # Ohm/mi seq zero
        x0     = dss.lines.x0
        entry  = (b2, name, length, r1, x1, r0, x0)
        graph[b1].append(entry)
        graph[b2].append((b1, name, length, r1, x1, r0, x0))
        flag = dss.lines.next()
    return graph


# não sei se vai quebrar com rede malhada, tomar cuidado aqui
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


def path_sequence_impedances(path: list[tuple]) -> tuple[complex, complex, float]:
    """
    Soma as impedancias de sequencia positiva e zero de cada segmento.
    Retorna (Z1_total [Ohm], Z0_total [Ohm], L_total [mi]).
    """
    Z1_total = 0 + 0j
    Z0_total = 0 + 0j
    L_total  = 0.0
    for (name, b1, b2, length, r1, x1, r0, x0) in path:
        Z1_total += complex(r1, x1) * length
        Z0_total += complex(r0, x0) * length
        L_total  += length
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

    Parametros
    ----------
    Va       : tensao fase A no relay durante a falta [V]
    Iabc     : correntes de fase (3,) no relay durante falta [A], sentido relay->falta
    Iabc_pre : correntes de fase (3,) no relay pre-falta [A], mesmo sentido
    Z1L      : impedancia total seq. positiva do caminho [Ohm]
    Z0L      : impedancia total seq. zero do caminho [Ohm]
    L_mi     : comprimento total do caminho [mi]
    """
    k0       = (Z0L - Z1L) / (3.0 * Z1L)
    I3I0     = Iabc[0] + Iabc[1] + Iabc[2]          # = 3*I0
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
# ETAPA 2 — CONDICOES PRE-FALTA
# =====================================================
V_pre    = get_bus_voltages(RELAY_BUS)

# CORREÇÃO 2: removido argumento terminal=2 (era o default anterior).
# get_line_currents agora usa terminal=1 por default — sem necessidade de argumento explícito.
# CORREÇÃO 3: removida a negação "-Iabc_pre_raw".
# Com terminal=1, a corrente já sai no sentido físico correto (relay -> rede),
# pois o terminal 1 de RELAY_LINE está conectado à barra do relay (RELAY_BUS).
# A negação anterior era um workaround para compensar a inversão de ~180° do terminal=2.
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

# CORREÇÃO 4: removido argumento implícito terminal=2.
# get_line_currents usa terminal=1 por default após a correção da assinatura.
I_3F = get_line_currents(RELAY_LINE)

section("CURTO TRIFASICO (3F)  —  barra relay  (fase A)")
pline("Icc3F", I_3F[0], Ibase, "A")

# =====================================================
# ETAPA 4 — CURTO MONOFASICO NA BARRA DO RELAY (A-terra)
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F1F Bus1={RELAY_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

# CORREÇÃO 5: idem etapa 3 — terminal=1 por default.
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
# Todos os fasores aqui vêm de leituras do terminal 1 (ver Etapas 2-4).
# Nenhuma corrente do terminal 2 é usada nesta etapa.
#
# Circuito pré-falta precisa estar ativo para leitura de potência.
# compile_circuit(add_meter=True) já foi chamado na Etapa 5; reutilizamos
# o estado atual (sem falta) que permanece ativo após get_thevenin_seq_impedances.
# Para garantir estado limpo, recompilamos explicitamente.
compile_circuit(add_meter=True)

# --- 1. Potência complexa no terminal 1 de RELAY_LINE (pré-falta) ---
# dss.cktelement.powers_mag_ang retorna [P1_A, ang1_A, P1_B, ang1_B, ...,
#                                         P2_A, ang2_A, ...] em kVA.
# Usamos apenas o terminal 1 (offset 0), fase A (índice 0 e 1).
# O fasor de potência S = P + jQ, onde ang é o ângulo de S em graus.
dss.circuit.set_active_element(RELAY_LINE)
pwr = dss.cktelement.powers
# Fase A do terminal 1: índices 0 (magnitude) e 1 (ângulo)
S_mag_kva = pwr[0]                           # |S| fase A, kVA
S_ang_deg = pwr[1]                           # ângulo de S, graus
S_phA     = polar_to_rect(S_mag_kva, S_ang_deg)  # S complexo fase A [kVA]
P_phA     = S_phA.real                       # potência ativa fase A [kW]
Q_phA     = S_phA.imag                       # potência reativa fase A [kvar]

# Fator de potência: pf = P / |S|  (convenção: positivo para carga indutiva)
# Clamp para evitar erro numérico em acos se |pf| > 1 por precisão float.
pf_raw = P_phA / abs(S_phA) if not np.isclose(abs(S_phA), 0.0) else 1.0
pf     = float(np.clip(pf_raw, -1.0, 1.0))

# --- 2. Ângulos dos fasores pré-falta (terminal 1, já disponíveis da Etapa 2) ---
theta_v_pre = np.angle(V_pre[0])             # ângulo tensão pré-falta fase A [rad]
theta_i_pre = np.angle(Iabc_pre[0])          # ângulo corrente pré-falta fase A [rad]
                                             # terminal 1, sem correção artificial

# --- 3. Ângulo de Thévenin conforme equação do artigo ---
# theta_vth = acos(pf) + theta_i_prefault
# acos(pf) é o ângulo de impedância (phi = ângulo entre V e I em carga pura),
# somado ao ângulo absoluto da corrente pré-falta para obter o ângulo absoluto de Vth.
phi       = np.arccos(pf)                    # ângulo de potência [rad], >= 0
theta_vth = phi + theta_i_pre                # ângulo absoluto de Vth [rad]

# --- 4. Tensão de Thévenin fasorial ---
# Magnitude = |V_pre fase A| (tensão linha-neutro medida na barra do relay).
# Ângulo    = theta_vth calculado acima.
Vth_mag = abs(V_pre[0])                      # [V]
Vth     = Vth_mag * np.exp(1j * theta_vth)  # fasor Vth [V]

# Tensão linha-linha equivalente derivada de Vth (para fórmulas do artigo).
VLL_art = Vth_mag * np.sqrt(3)              # [V]

# --- 5. Fator k = |Vth| / Vbase_LN ---
# Representa o nível de tensão normalizado. Se tensão = 1 pu, k = 1.
# Garante que as fórmulas do artigo funcionem com tensão real medida.
k = Vth_mag / Vln

# --- 6. Impedâncias pelo método do artigo ---
# Correntes de curto do terminal 1 (Etapas 3 e 4), fase A.
Icc3ph_mag = abs(I_3F[0])                   # [A]  — terminal 1
Icc1ph_mag = abs(I_1F[0])                   # [A]  — terminal 1

# Fórmulas do artigo (escalar de magnitudes, resultado real positivo):
#   Z1eq_art = k * VLL / (sqrt(3) * Icc_3ph)
#   Z0eq_art = sqrt(3) * k * VLL / Icc_1ph  -  2 * Z1eq_art
Z1eq_art_mag = (k * VLL_art) / (np.sqrt(3) * Icc3ph_mag)
Z0eq_art_mag = (np.sqrt(3) * k * VLL_art / Icc1ph_mag) - 2.0 * Z1eq_art_mag

# Recompõe fasores usando o ângulo de Vth como referência angular do sistema,
# e o ângulo de cada impedância derivado das correntes de curto.
# Z = V/I -> ang(Z1) = ang(Vth) - ang(I_3F_phA)
# Isso preserva a fase correta de cada impedância para uso posterior.
ang_Z1_art = theta_vth - np.angle(I_3F[0])
ang_Z0_art = theta_vth - np.angle(I_1F[0])  # aproximação via sequência zero
Z1eq_art = Z1eq_art_mag * np.exp(1j * ang_Z1_art)
Z0eq_art = Z0eq_art_mag * np.exp(1j * ang_Z0_art)

# --- 7. Comparação com impedâncias do método atual (Etapa 5 / Zbus) ---
def _pct_err(val: float, ref: float) -> float:
    """Erro percentual de magnitude em relação à referência (método Zbus)."""
    return (val - ref) / ref * 100.0 if not np.isclose(ref, 0.0) else float("nan")

err_Z1_mag = _pct_err(abs(Z1eq_art), abs(Z1eq))
err_Z0_mag = _pct_err(abs(Z0eq_art), abs(Z0eq))
err_Z1_ang = np.degrees(ang_Z1_art) - np.degrees(np.angle(Z1eq))  # graus
err_Z0_ang = np.degrees(ang_Z0_art) - np.degrees(np.angle(Z0eq))  # graus

# --- 8. Impressão da validação ---
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
print(f"  {'Barra':<8} {'L caminho (mi)':>15}  {'|Z1L| (Ohm)':>12}  {'|Z0L| (Ohm)':>12}  Segmentos")
print(f"  {'-' * W}")

paths_cache: dict[str, tuple] = {}
for fault_bus in FAULT_BUSES:
    path          = find_shortest_path(graph, RELAY_BUS, fault_bus)
    Z1L, Z0L, L  = path_sequence_impedances(path)
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

    # CORREÇÃO 6: removido argumento implícito terminal=2 e removida negação.
    # Antes: get_line_currents(RELAY_LINE, n_phases=3)  -> terminal=2 (default antigo)
    #        Iabc_fault = -Iabc_fault_raw               -> negação compensatória
    # Agora: get_line_currents(RELAY_LINE, n_phases=3)  -> terminal=1 (novo default)
    #        sem negação, sentido físico já está correto.
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
        # pct = erro/ref * 100
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