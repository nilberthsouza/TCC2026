"""
main.py
-------
Localizador de faltas — algoritmo de Takagi Modificado.

Fluxo principal: configuração → pré-falta → curtos de referência →
Thévenin → grafo → Takagi multi-folha por barra de falta → resumo.
"""

import numpy as np
import py_dss_interface

from circuit_utils  import (compile_circuit, get_bus_voltages,
                             get_line_currents, compute_bases,
                             get_thevenin_seq_impedances)
from topology_utils import (build_networkx_graph, calc_ref_distances,
                             calc_feeder_length, calc_feeder_farthest_bus,
                             build_network_graph, find_shortest_path,
                             path_sequence_impedances, find_feeder_path,
                             find_leaves, get_all_distances_from_relay,
                             find_nearest_bus, build_leaves_cache,
                             _norm_bus, find_relay_line)
from takagi         import takagi_1ph, takagi_3ph
from display_utils  import (section, pline, fmt_z, W,
                             print_bases, print_thevenin, print_debug_1ph,
                             print_fault_header, print_valid_results,
                             print_discarded_results, print_consolidated_table)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
SISTEMA = 1

if SISTEMA == 1:
    DSS_FILE    = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal14mi.dss"
    RELAY_BUS   = "812"
    FAULT_BUSES = ["850", "854", "822", "834", "840", "848"]

elif SISTEMA == 2:
    DSS_FILE    = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\69bus.dss"
    RELAY_BUS   = "2"   # primeira barra downstream do slack (bus2 da linha l1_2)
    FAULT_BUSES = ["19", "27", "32", "36", "38", "45"]

SBASE_MVA = 40.0
SBASE     = SBASE_MVA * 1e6

dss = py_dss_interface.DSS()

# Detecta automaticamente a linha do relay:
# busca a linha cujo bus2 == RELAY_BUS (corrente entra pelo terminal 1, sentido fonte→rede)
_dss_tmp = py_dss_interface.DSS()
_dss_tmp.text(f"compile {DSS_FILE}")
_dss_tmp.text("CalcVoltageBases")
_dss_tmp.solution.solve()
RELAY_LINE = find_relay_line(_dss_tmp, RELAY_BUS)
print(f"  RELAY_LINE detectada automaticamente: {RELAY_LINE}")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 0 — DISTÂNCIAS DE REFERÊNCIA E COMPRIMENTO DO ALIMENTADOR
# ─────────────────────────────────────────────────────────────────────────────
_G               = build_networkx_graph(DSS_FILE)
REF              = calc_ref_distances(_G, RELAY_BUS, FAULT_BUSES)
L_ALIMENTADOR_MI = calc_feeder_length(RELAY_BUS, _G)
FARTHEST_BUS     = calc_feeder_farthest_bus(RELAY_BUS, _G)

section("ETAPA 0 — DISTÂNCIAS DE REFERÊNCIA E COMPRIMENTO DO ALIMENTADOR")
print(f"  Relay bus          : {RELAY_BUS}")
print(f"  Barra mais distante: {FARTHEST_BUS}")
print(f"  L_ALIMENTADOR_MI   : {L_ALIMENTADOR_MI:.4f} mi")
print(f"")
print(f"  {'Barra':<8} {'Distância (mi)':>15}")
print(f"  {'-' * 26}")
for fb, d in REF.items():
    print(f"  {fb:<8} {d:>15.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1 — BASES DO SISTEMA
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE)
Vln, Vll, Ibase, Zbase = compute_bases(dss, RELAY_BUS, SBASE)
print_bases(RELAY_BUS, RELAY_LINE, SBASE_MVA, Vln, Vll, Ibase, Zbase)

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 2 — CONDIÇÕES PRÉ-FALTA
# ─────────────────────────────────────────────────────────────────────────────
V_pre    = get_bus_voltages(dss, RELAY_BUS)
Iabc_pre = get_line_currents(dss, RELAY_LINE)

section("CONDIÇÕES PRÉ-FALTA  —  barra relay  (fase A)")
pline("Tensão Va_pre",   V_pre[0],    Vln,   "V")
pline("Corrente Ia_pre", Iabc_pre[0], Ibase, "A")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 3 — CURTO TRIFÁSICO NA BARRA DO RELAY
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
dss.text(f"New Fault.F3F Bus1={RELAY_BUS} Phases=3 R=0.0001")
dss.solution.solve()
I_3F = get_line_currents(dss, RELAY_LINE)

section("CURTO TRIFÁSICO (3F)  —  barra relay  (fase A)")
pline("Icc3F", I_3F[0], Ibase, "A")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 4 — CURTO MONOFÁSICO NA BARRA DO RELAY (A-terra)
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
dss.text(f"New Fault.F1F Bus1={RELAY_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()
I_1F = get_line_currents(dss, RELAY_LINE)

section("CURTO MONOFÁSICO 1F-T  —  barra relay  (fase A)")
pline("Icc1F", I_1F[0], Ibase, "A")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 5 — IMPEDÂNCIAS DE THÉVENIN
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
Z0eq, Z1eq = get_thevenin_seq_impedances(dss, RELAY_BUS)
print_thevenin(Z0eq, Z1eq, Zbase)

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 5b — VALIDAÇÃO THÉVENIN / MÉTODO DO ARTIGO
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
dss.circuit.set_active_element(RELAY_LINE)
pwr   = dss.cktelement.powers
S_phA = pwr[0] * (np.cos(np.deg2rad(pwr[1])) + 1j * np.sin(np.deg2rad(pwr[1])))
P_phA = S_phA.real
Q_phA = S_phA.imag

pf_raw      = P_phA / abs(S_phA) if not np.isclose(abs(S_phA), 0.0) else 1.0
pf          = float(np.clip(pf_raw, -1.0, 1.0))
theta_v_pre = np.angle(V_pre[0])
theta_i_pre = np.angle(Iabc_pre[0])
phi         = np.arccos(pf)
theta_vth   = phi + theta_i_pre
Vth_mag     = abs(V_pre[0])
Vth         = Vth_mag * np.exp(1j * theta_vth)
VLL_art     = Vth_mag * np.sqrt(3)
k           = Vth_mag / Vln
Icc3ph_mag  = abs(I_3F[0])
Icc1ph_mag  = abs(I_1F[0])
Z1eq_art_mag = (k * VLL_art) / (np.sqrt(3) * Icc3ph_mag)
Z0eq_art_mag = (np.sqrt(3) * k * VLL_art / Icc1ph_mag) - 2.0 * Z1eq_art_mag
ang_Z1_art  = theta_vth - np.angle(I_3F[0])
ang_Z0_art  = theta_vth - np.angle(I_1F[0])
Z1eq_art    = Z1eq_art_mag * np.exp(1j * ang_Z1_art)
Z0eq_art    = Z0eq_art_mag * np.exp(1j * ang_Z0_art)

def _pct_err(val, ref):
    return (val - ref) / ref * 100.0 if not np.isclose(ref, 0.0) else float("nan")

err_Z1_mag = _pct_err(abs(Z1eq_art), abs(Z1eq))
err_Z0_mag = _pct_err(abs(Z0eq_art), abs(Z0eq))
err_Z1_ang = np.degrees(ang_Z1_art) - np.degrees(np.angle(Z1eq))
err_Z0_ang = np.degrees(ang_Z0_art) - np.degrees(np.angle(Z0eq))

section("ETAPA 5b — VALIDAÇÃO THÉVENIN / MÉTODO DO ARTIGO")
print(f"\n  [ Potência pré-falta — terminal 1, fase A ]")
print(f"  P  : {P_phA:>+12.4f} kW    Q  : {Q_phA:>+12.4f} kvar    |S| : {abs(S_phA):>12.4f} kVA")
print(f"  pf : {pf:>12.6f}   (= cos {np.degrees(phi):>+.4f} deg)")
print(f"\n  [ Impedâncias — comparação ]")
print(f"  {'':20} {'Artigo':>28}   {'Código (Zbus)':>28}   {'Erro |Z|':>9}  {'Erro ang':>9}")
print(f"  {'-' * 102}")
print(f"  {'Z1eq':<20} {fmt_z(Z1eq_art, Zbase)}   {fmt_z(Z1eq, Zbase)}"
      f"   {err_Z1_mag:>+8.3f}%  {err_Z1_ang:>+8.3f}°")
print(f"  {'Z0eq':<20} {fmt_z(Z0eq_art, Zbase)}   {fmt_z(Z0eq, Zbase)}"
      f"   {err_Z0_mag:>+8.3f}%  {err_Z0_ang:>+8.3f}°")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 6 — GRAFO DA REDE + PRÉ-PROCESSAMENTO DE FOLHAS
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
graph = build_network_graph(dss)

# Detecta slack bus: se RELAY_BUS == nó raiz do circuito, modo automático
slack_bus = dss.circuit.name   # nome do circuito == nome do elemento source
# Alternativa robusta: pegar a primeira barra da lista de barras do OpenDSS
all_buses_raw = dss.circuit.buses_names
# O slack real é a barra do elemento "Vsource.source" ou "Circuit.xxx"
# Usamos heurística: barra com nome igual ao circuit name, ou barra 1
try:
    dss.circuit.set_active_element("Vsource.source")
    slack_bus_name = dss.cktelement.bus_names[0].split(".")[0].lower()
except Exception:
    slack_bus_name = all_buses_raw[0].lower() if all_buses_raw else ""

relay_is_slack = (_norm_bus(RELAY_BUS) == slack_bus_name)

# Lista de barras de falta: FAULT_BUSES normal, ou todas as barras se relay=slack
if relay_is_slack:
    # Todas as barras exceto o relay, em ordem
    fault_bus_list = [b for b in all_buses_raw
                      if _norm_bus(b) != _norm_bus(RELAY_BUS)]
else:
    fault_bus_list = FAULT_BUSES

# Folhas e caches
leaves              = find_leaves(graph, RELAY_BUS)
leaves_cache        = build_leaves_cache(graph, RELAY_BUS, leaves)
distances_from_relay = get_all_distances_from_relay(graph, RELAY_BUS)

# Distâncias de referência para TODAS as barras de falta
REF_ALL = calc_ref_distances(_G, RELAY_BUS, fault_bus_list)

section("FOLHAS DO ALIMENTADOR")
print(f"  Total de folhas encontradas: {len(leaves)}")
print(f"  {'Folha':<12} {'L relay→folha (mi)':>20}")
print(f"  {'-' * 34}")
for lf, (_, _, _, L_lf) in leaves_cache.items():
    print(f"  {lf:<12} {L_lf:>20.4f}")

section("GRAFO DA REDE  —  distâncias acumuladas (relay → cada barra)")
print(f"  {'Barra':<12} {'Dist. relay (mi)':>18}")
print(f"  {'-' * 32}")
for bus, dist in sorted(distances_from_relay.items(), key=lambda x: x[1]):
    print(f"  {bus:<12} {dist:>18.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 7 — TAKAGI MULTI-FOLHA POR BARRA DE FALTA
# ─────────────────────────────────────────────────────────────────────────────
section("LOCALIZADOR DE TAKAGI MODIFICADO  —  multi-folha  —  falta 1F-T fase A")

consolidated: list[tuple | None] = []   # para tabela final (modo slack)
first_fault = True                       # controla bloco debug

for fault_bus in fault_bus_list:

    ref_dist = REF_ALL.get(fault_bus, float("nan"))

    # Simula falta
    compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
    dss.text(f"New Fault.F1F Bus1={fault_bus}.1.0 Phases=1 R=0.0001")
    dss.solution.solve()

    V_fault    = get_bus_voltages(dss, RELAY_BUS)
    Iabc_fault = get_line_currents(dss, RELAY_LINE, n_phases=3)

    # ── DEBUG: apenas primeira barra (modo FAULT_BUSES normal) ───────────────
    if first_fault and not relay_is_slack and leaves_cache:
        first_leaf       = next(iter(leaves_cache))
        path_d, Z1d, Z0d, Ld = leaves_cache[first_leaf]
        k0        = (Z0d - Z1d) / (3.0 * Z1d)
        I3I0_f    = Iabc_fault[0] + Iabc_fault[1] + Iabc_fault[2]
        Icomp_f   = Iabc_fault[0] + k0 * I3I0_f
        I3I0_p    = Iabc_pre[0] + Iabc_pre[1] + Iabc_pre[2]
        Icomp_p   = Iabc_pre[0] + k0 * I3I0_p
        dIcomp    = Icomp_f - Icomp_p
        num_d     = np.imag(V_fault[0] * np.conj(dIcomp))
        den_d     = np.imag(Z1d * Icomp_f * np.conj(dIcomp))
        d_dbg     = (num_d / den_d) * Ld if not np.isclose(den_d, 0.0) else float("nan")
        print_debug_1ph(
            fault_bus=fault_bus, ref_dist=ref_dist,
            Z1L=Z1d, Z0L=Z0d,
            Va_f=V_fault[0], V_pre_a=V_pre[0],
            Iabc_fault=Iabc_fault, Iabc_pre=Iabc_pre,
            I3I0_f=I3I0_f, I3I0_p=I3I0_p,
            Icomp_f=Icomp_f, Icomp_p=Icomp_p,
            dIcomp=dIcomp, num=num_d, den=den_d, d_mi=d_dbg,
        )
        first_fault = False
    # ── fim debug ─────────────────────────────────────────────────────────────

    print_fault_header(fault_bus, ref_dist)

    valid_rows    = []
    discarded_rows = []
    best_row      = None   # (erro_abs, row_tuple) para tabela consolidada

    for leaf, (path, Z1L, Z0L, L_folha) in leaves_cache.items():

        d_mi = takagi_1ph(
            Va       = V_fault[0],
            Iabc     = Iabc_fault,
            Iabc_pre = Iabc_pre,
            Z1L      = Z1L,
            Z0L      = Z0L,
            L_mi     = L_folha,
        )

        # Critério de descarte
        if d_mi is None:
            discarded_rows.append((leaf, None, L_folha, "denominador nulo"))
            continue
        if d_mi <= 0:
            discarded_rows.append((leaf, d_mi, L_folha, "negativo"))
            continue
        if d_mi > L_folha:
            discarded_rows.append((leaf, d_mi, L_folha, "excede comprimento"))
            continue

        # Caminho válido — encontra barra candidata
        cand_bus  = find_nearest_bus(distances_from_relay, d_mi, path)
        dist_real = distances_from_relay.get(cand_bus, float("nan"))
        erro_mi   = d_mi - ref_dist
        erro_pct  = erro_mi / L_ALIMENTADOR_MI * 100.0 if L_ALIMENTADOR_MI else float("nan")

        valid_rows.append((leaf, d_mi, cand_bus, dist_real, erro_mi, erro_pct))

        # Atualiza melhor resultado (menor erro absoluto)
        if best_row is None or abs(erro_mi) < best_row[0]:
            best_row = (abs(erro_mi),
                        (fault_bus, leaf, cand_bus, dist_real, d_mi, erro_mi, erro_pct))

    print_valid_results(valid_rows)
    print_discarded_results(discarded_rows)

    consolidated.append(best_row[1] if best_row else None)

# ─────────────────────────────────────────────────────────────────────────────
# TABELA CONSOLIDADA (sempre impressa — resume o melhor resultado por falta)
# ─────────────────────────────────────────────────────────────────────────────
print_consolidated_table([r for r in consolidated if r is not None])

# ─────────────────────────────────────────────────────────────────────────────
# RESTAURA CIRCUITO ORIGINAL
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE)