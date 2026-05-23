"""
main.py
-------
Localizador de faltas — algoritmo de Takagi Modificado.

Fluxo principal: configuração → pré-falta → curtos de referência →
Thévenin → grafo → Takagi por barra de falta → resumo.
"""

import numpy as np
import py_dss_interface

from circuit_utils   import (compile_circuit, get_bus_voltages,
                              get_line_currents, compute_bases,
                              get_thevenin_seq_impedances)
from linecode_utils  import get_linecode_params
from topology_utils  import (build_networkx_graph, calc_ref_distances,
                              calc_feeder_length, calc_feeder_farthest_bus,
                              build_network_graph, find_shortest_path,
                              path_sequence_impedances, find_feeder_path)
from takagi          import takagi_1ph, takagi_3ph
from display_utils   import (section, pline, fmt_z, W,
                              print_bases, print_linecode,
                              print_thevenin, print_debug_1ph)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────────────────────
#DSS_FILE     = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal14mi.dss"
DSS_FILE     = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\69bus.dss"

#RELAY_BUS    = "812"
RELAY_BUS    = "12"
#RELAY_LINE   ="Line.L5"
RELAY_LINE   ="Line.L11_12"
#FAULT_BUSES  = ["850","854","822","834","840","848"]
FAULT_BUSES  = ["19","27","32","36","38","45",]

REF_LINECODE = "300"
SBASE_MVA    = 40.0
SBASE        = SBASE_MVA * 1e6

dss = py_dss_interface.DSS()

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
print(f"  L_ALIMENTADOR_MI   : {L_ALIMENTADOR_MI:.4f} mi  (barra mais distante alcançável)")
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
# ETAPA 1b — PARÂMETROS DO LINECODE DE REFERÊNCIA
# ─────────────────────────────────────────────────────────────────────────────
r1_ref, x1_ref, r0_ref, x0_ref = get_linecode_params(dss, REF_LINECODE)
Z1_ref_per_mi = complex(r1_ref, x1_ref)
Z0_ref_per_mi = complex(r0_ref, x0_ref)
print_linecode(REF_LINECODE, r1_ref, x1_ref, r0_ref, x0_ref)

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 1c — IMPEDÂNCIAS DO ALIMENTADOR INTEIRO (relay -> barra mais distante)
# ─────────────────────────────────────────────────────────────────────────────
# Calculado aqui (pós compile_circuit) para ter o grafo OpenDSS disponível.
# Z1L_feed e Z0L_feed são impedâncias PURAS [Ohm] — usadas por Takagi.
# Takagi retornará d_pu = num/den, convertido para d_mi = d_pu * L_ALIMENTADOR_MI.

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
pwr     = dss.cktelement.powers
S_phA   = pwr[0] * (np.cos(np.deg2rad(pwr[1])) + 1j * np.sin(np.deg2rad(pwr[1])))
P_phA   = S_phA.real
Q_phA   = S_phA.imag

pf_raw  = P_phA / abs(S_phA) if not np.isclose(abs(S_phA), 0.0) else 1.0
pf      = float(np.clip(pf_raw, -1.0, 1.0))

theta_v_pre = np.angle(V_pre[0])
theta_i_pre = np.angle(Iabc_pre[0])
phi         = np.arccos(pf)
theta_vth   = phi + theta_i_pre

Vth_mag    = abs(V_pre[0])
Vth        = Vth_mag * np.exp(1j * theta_vth)
VLL_art    = Vth_mag * np.sqrt(3)
k          = Vth_mag / Vln

Icc3ph_mag = abs(I_3F[0])
Icc1ph_mag = abs(I_1F[0])

Z1eq_art_mag = (k * VLL_art) / (np.sqrt(3) * Icc3ph_mag)
Z0eq_art_mag = (np.sqrt(3) * k * VLL_art / Icc1ph_mag) - 2.0 * Z1eq_art_mag

ang_Z1_art = theta_vth - np.angle(I_3F[0])
ang_Z0_art = theta_vth - np.angle(I_1F[0])
Z1eq_art   = Z1eq_art_mag * np.exp(1j * ang_Z1_art)
Z0eq_art   = Z0eq_art_mag * np.exp(1j * ang_Z0_art)

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
print(f"  theta_v_pre  : {np.degrees(theta_v_pre):>+12.4f} deg")
print(f"  theta_i_pre  : {np.degrees(theta_i_pre):>+12.4f} deg")
print(f"  phi = acos(pf): {np.degrees(phi):>+12.4f} deg")
print(f"  theta_vth    : {np.degrees(theta_vth):>+12.4f} deg  (= phi + theta_i_pre)")
print(f"\n  [ Tensão de Thévenin ]")
pline("Vth",  Vth, Vln, "V")
print(f"  VLL_art      : {VLL_art:>12.4f} V    (= |Vth| * sqrt(3))")
print(f"  k = |Vth|/Vln: {k:>12.6f} pu")
print(f"\n  [ Correntes de curto — terminal 1 ]")
pline("I_3F fase A", I_3F[0], Ibase, "A")
pline("I_1F fase A", I_1F[0], Ibase, "A")
print(f"\n  [ Impedâncias — comparação ]")
print(f"  {'':20} {'Artigo':>28}   {'Código (Zbus)':>28}   {'Erro |Z|':>9}  {'Erro ang':>9}")
print(f"  {'-' * 102}")
print(f"  {'Z1eq':<20} {fmt_z(Z1eq_art, Zbase)}   {fmt_z(Z1eq, Zbase)}"
      f"   {err_Z1_mag:>+8.3f}%  {err_Z1_ang:>+8.3f}°")
print(f"  {'Z0eq':<20} {fmt_z(Z0eq_art, Zbase)}   {fmt_z(Z0eq, Zbase)}"
      f"   {err_Z0_mag:>+8.3f}%  {err_Z0_ang:>+8.3f}°")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 6 — GRAFO DA REDE + CAMINHOS
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
graph = build_network_graph(dss)

# Caminho completo relay -> barra mais distante (alimentador inteiro)
feeder_path          = find_feeder_path(graph, RELAY_BUS, FARTHEST_BUS)
Z1L_feed, Z0L_feed, L_feed = path_sequence_impedances(feeder_path)

section("GRAFO DA REDE  —  caminhos relay -> barra de falta")
print(f"  Alimentador inteiro: {RELAY_BUS} -> {FARTHEST_BUS}")
print(f"  Z1L_feed : {abs(Z1L_feed):.6f} Ohm  angle {np.degrees(np.angle(Z1L_feed)):>+.3f} deg  (impedância pura, alimentador completo)")
print(f"  Z0L_feed : {abs(Z0L_feed):.6f} Ohm  angle {np.degrees(np.angle(Z0L_feed)):>+.3f} deg")
print(f"  L_feed   : {L_feed:.4f} mi")
print(f"")
print(f"  {'Barra':<8} {'L caminho (mi)':>15}  {'|Z1L| (Ohm)':>14}  {'|Z0L| (Ohm)':>14}  Segmentos")
print(f"  {'-' * W}")

paths_cache: dict[str, tuple] = {}
for fault_bus in FAULT_BUSES:
    path             = find_shortest_path(graph, RELAY_BUS, fault_bus)
    Z1L, Z0L, L     = path_sequence_impedances(path)
    paths_cache[fault_bus] = (path, Z1L, Z0L, L)
    segs = " -> ".join(f"[{s[0]}]({s[3]:.4f}mi)" for s in path)
    print(f"  {fault_bus:<8} {L:>15.4f}  {abs(Z1L):>12.6f}  {abs(Z0L):>12.6f}  {segs}")

# ─────────────────────────────────────────────────────────────────────────────
# ETAPA 7 — TAKAGI MODIFICADO PARA CADA BARRA DE FALTA
# ─────────────────────────────────────────────────────────────────────────────
section("LOCALIZADOR DE TAKAGI MODIFICADO  —  falta 1F-T fase A")
print(f"  {'Barra':<8} {'d (mi)':>10}  {'Ref (mi)':>10}  {'Erro (mi)':>10}  {'Erro (%)':>10}")
print(f"  {'-' * 56}")

resultados: list[tuple] = []

for fault_bus in FAULT_BUSES:
    compile_circuit(dss, DSS_FILE, RELAY_LINE, add_meter=True)
    dss.text(f"New Fault.F1F Bus1={fault_bus}.1.0 Phases=1 R=0.0001")
    dss.solution.solve()

    V_fault    = get_bus_voltages(dss, RELAY_BUS)
    Iabc_fault = get_line_currents(dss, RELAY_LINE, n_phases=3)

    path, Z1L_path, Z0L_path, L_path = paths_cache[fault_bus]

    # Takagi usa impedância do alimentador INTEIRO (relay -> barra mais distante).
    # Não usa o caminho até a falta, pois o relay não sabe onde ela está.
    # Resultado: d_pu = num/den, convertido para d_mi = d_pu * L_ALIMENTADOR_MI.
    d_mi = takagi_1ph(
        Va       = V_fault[0],
        Iabc     = Iabc_fault,
        Iabc_pre = Iabc_pre,
        Z1L      = Z1L_feed,
        Z0L      = Z0L_feed,
        L_mi     = L_ALIMENTADOR_MI,
    )

    # ── DEBUG: apenas para a primeira barra ──────────────────────────────────
    if fault_bus == FAULT_BUSES[0]:
        k0        = (Z0L_feed - Z1L_feed) / (3.0 * Z1L_feed)
        I3I0_f    = Iabc_fault[0] + Iabc_fault[1] + Iabc_fault[2]
        Icomp_f   = Iabc_fault[0] + k0 * I3I0_f
        I3I0_p    = Iabc_pre[0] + Iabc_pre[1] + Iabc_pre[2]
        Icomp_p   = Iabc_pre[0] + k0 * I3I0_p
        dIcomp    = Icomp_f - Icomp_p
        num_d     = np.imag(V_fault[0] * np.conj(dIcomp))
        den_d     = np.imag(Z1L_feed * Icomp_f * np.conj(dIcomp))
        d_dbg     = (num_d / den_d) * L_ALIMENTADOR_MI if not np.isclose(den_d, 0.0) else float("nan")

        print_debug_1ph(
            fault_bus=fault_bus, ref_dist=REF.get(fault_bus, "?"),
            Z1L=Z1L_feed, Z0L=Z0L_feed,
            Va_f=V_fault[0], V_pre_a=V_pre[0],
            Iabc_fault=Iabc_fault, Iabc_pre=Iabc_pre,
            I3I0_f=I3I0_f, I3I0_p=I3I0_p,
            Icomp_f=Icomp_f, Icomp_p=Icomp_p,
            dIcomp=dIcomp, num=num_d, den=den_d, d_mi=d_dbg,
        )
    # ── fim debug ─────────────────────────────────────────────────────────────

    ref = REF.get(fault_bus, float("nan"))
    if d_mi is not None:
        erro = d_mi - ref
        pct  = erro / 14 * 100
        print(f"  {fault_bus:<8} {d_mi:>10.4f}  {ref:>10.3f}  {erro:>+10.4f}  {pct:>+10.2f}%")
        resultados.append((fault_bus, d_mi, ref, V_fault[0]))
    else:
        print(f"  {fault_bus:<8} {'---':>10}  {ref:>10.3f}  denominador nulo")

# ─────────────────────────────────────────────────────────────────────────────
# RESUMO FINAL
# ─────────────────────────────────────────────────────────────────────────────
section("RESUMO")
print(f"  {'Barra':<8} {'d Takagi (mi)':>14}  {'Ref (mi)':>10}  {'Erro (mi)':>10}  "
      f"{'Erro (%)':>10}  {'|Va| (V)':>12}  {'Va (pu)':>10}  {'ang (deg)':>10}")
print(f"  {'-' * 96}")
for bus, d_mi, ref, Va in resultados:
    erro   = d_mi - ref
    pct    = abs(erro / 14 * 100)
    Va_mag = abs(Va)
    Va_pu  = Va_mag / Vln
    Va_ang = np.degrees(np.angle(Va))
    print(f"  {bus:<8} {d_mi:>14.4f}  {ref:>10.3f}  {erro:>+10.4f}  {pct:>+10.2f}%"
          f"  {Va_mag:>12.4f}  {Va_pu:>10.6f}  {Va_ang:>+10.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# RESTAURA CIRCUITO ORIGINAL
# ─────────────────────────────────────────────────────────────────────────────
compile_circuit(dss, DSS_FILE, RELAY_LINE)
