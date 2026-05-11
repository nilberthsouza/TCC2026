import py_dss_interface
import numpy as np

dss = py_dss_interface.DSS()

# =====================================================
# CONFIGURAÇÕES
# =====================================================
#DSS_FILE       = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss"
DSS_FILE       = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal14mi.dss"
RELAY_BUS      = "812"
RELAY_LINE     = "Line.L5"       # linha monitorada (terminal 2 = lado do relay)
FAULT_BUSES    = ["850", "854", "822", "834", "840", "848"]
LINE_LENGTH_MI = 953 / 1000      # comprimento TOTAL da linha monitorada em milhas
Sbase_MVA      = 40.0
Sbase          = Sbase_MVA * 1e6

# Operador de Fortescue e sua inversa
_a   = np.exp(1j * 2 * np.pi / 3)
A    = np.array([[1,    1,      1    ],
                 [1,    _a**2,  _a   ],
                 [1,    _a,     _a**2]], dtype=complex)
Ainv = np.linalg.inv(A)


# =====================================================
# FUNÇÕES UTILITÁRIAS
# =====================================================

def compile_circuit(add_meter: bool = False) -> None:
    """Recompila o circuito base e opcionalmente adiciona EnergyMeter."""
    dss.text(f"compile {DSS_FILE}")
    if add_meter:
        dss.text(f"New EnergyMeter.M1 Element={RELAY_LINE} Terminal=1")
    dss.solution.solve()


def polar_to_rect(mag: float, ang_deg: float) -> complex:
    """Magnitude + ângulo em graus → número complexo (NumPy puro)."""
    ang = np.deg2rad(ang_deg)
    return mag * (np.cos(ang) + 1j * np.sin(ang))


def get_bus_voltages(bus: str, n_phases: int = 3) -> np.ndarray:
    """Retorna array complexo (n_phases,) das tensões de fase na barra."""
    dss.circuit.set_active_bus(bus)
    v = dss.bus.vmag_angle
    return np.array([polar_to_rect(v[2*k], v[2*k+1]) for k in range(n_phases)],
                    dtype=complex)


def get_line_currents(element: str, terminal: int = 2, n_phases: int = 3) -> np.ndarray:
    """
    Retorna array complexo (n_phases,) das correntes no terminal indicado.
    terminal=1 → offset 0; terminal=2 → offset 6.
    """
    dss.circuit.set_active_element(element)
    curr   = dss.cktelement.currents_mag_ang
    offset = (terminal - 1) * 2 * n_phases
    return np.array([polar_to_rect(curr[offset + 2*k], curr[offset + 2*k+1])
                     for k in range(n_phases)], dtype=complex)


def abc_to_012(vec: np.ndarray) -> np.ndarray:
    """Transformada de Fortescue: ABC → sequências 0-1-2."""
    return Ainv @ vec


def compute_bases(bus: str) -> tuple[float, float, float, float]:
    """
    Calcula bases do sistema na barra informada.
    Retorna (Vbase_ln [V], Vbase_ll [V], Ibase [A], Zbase [Ω]).
    """
    dss.circuit.set_active_bus(bus)
    Vln   = dss.bus.kv_base * 1e3
    Vll   = Vln * np.sqrt(3)
    Ibase = Sbase / (np.sqrt(3) * Vll)
    Zbase = Vll**2 / Sbase
    return Vln, Vll, Ibase, Zbase


def get_thevenin_seq_impedances(bus: str) -> tuple[complex, complex]:
    """
    Calcula Z0eq e Z1eq de Thévenin na barra via Zbus = pinv(Ybus).
    Retorna (Z0eq, Z1eq) em Ω.
    """
    y_flat = dss.circuit.system_y
    y_cplx = np.array(y_flat[0::2]) + 1j * np.array(y_flat[1::2])
    n      = int(np.sqrt(len(y_cplx)))
    Ybus   = y_cplx.reshape((n, n))
    Zbus   = np.linalg.pinv(Ybus)

    nodes = dss.circuit.y_node_order
    idx   = [nodes.index(f"{bus}.1"),
             nodes.index(f"{bus}.2"),
             nodes.index(f"{bus}.3")]

    Zabc = Zbus[np.ix_(idx, idx)]
    Z012 = Ainv @ Zabc @ A
    return Z012[0, 0], Z012[1, 1]   # Z0eq, Z1eq


def get_line_series_impedance(element: str) -> complex:
    """
    Extrai a impedância série total de sequência positiva da linha (Ω).
    Usa os parâmetros diretos via dss.lines:
      ZL = (R1 + jX1) * length
    onde R1 e X1 estão em Ω/unidade-de-comprimento e length na mesma unidade.
    """
    line_name = element.split(".")[-1]
    dss.lines.name = line_name
    r1     = dss.lines.r1       # Ω/unidade
    x1     = dss.lines.x1       # Ω/unidade
    length = dss.lines.length   # unidade de comprimento (consistente com r1/x1)
    return complex(r1 * length, x1 * length)

def takagi(Vs: complex, Is: complex, Is_pre: complex, ZL: complex) -> float | None:
    """
    Distância da falta em p.u. pelo método de Takagi.
      d = Im(Vs · ΔIs*) / Im(ZL · Is · ΔIs*)
    Retorna None se o denominador for nulo.
    """
    dI      = Is - Is_pre
    dI_conj = np.conj(dI)
    num     = np.imag(Vs * dI_conj)
    den     = np.imag(ZL * Is * dI_conj)
    return None if np.isclose(den, 0.0) else num / den


# =====================================================
# HELPERS DE IMPRESSÃO
# =====================================================
W = 62

def section(title: str) -> None:
    print(f"\n{'=' * W}")
    print(f"  {title}")
    print(f"{'=' * W}")


def fmt(val: complex, base: float, unit: str) -> str:
    """Formata valor complexo: real (mag ∠ ang) e pu lado a lado."""
    mag    = abs(val)
    ang    = np.degrees(np.angle(val))
    mag_pu = mag / base
    return (f"{mag:>12.4f} {unit} ∠ {ang:>+7.2f}°  "
            f"({val.real:>+10.4f}{val.imag:>+10.4f}j)  "
            f"→  {mag_pu:.6f} pu")


def pline(label: str, val: complex, base: float, unit: str) -> None:
    print(f"  {label:<18} {fmt(val, base, unit)}")


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
print(f"  Zbase              : {Zbase:.6f} Ω")

# =====================================================
# ETAPA 2 — CONDIÇÕES PRÉ-FALTA
# =====================================================
V_pre = get_bus_voltages(RELAY_BUS)    # (3,) [V]
I_pre = get_line_currents(RELAY_LINE)  # (3,) [A]

section("CONDIÇÕES PRÉ-FALTA  —  barra relay  (fase A)")
pline("Tensão Va_pre",   V_pre[0], Vln,   "V")
pline("Corrente Ia_pre", I_pre[0], Ibase, "A")

# =====================================================
# ETAPA 3 — CURTO TRIFÁSICO NA BARRA DO RELAY
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F3F Bus1={RELAY_BUS} Phases=3 R=0.0001")
dss.solution.solve()
I_3F = get_line_currents(RELAY_LINE)

section("CURTO TRIFÁSICO (3F)  —  barra relay  (fase A)")
pline("Icc3F", I_3F[0], Ibase, "A")

# =====================================================
# ETAPA 4 — CURTO MONOFÁSICO NA BARRA DO RELAY (A-terra)
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F1F Bus1={RELAY_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()
I_1F = get_line_currents(RELAY_LINE)

section("CURTO MONOFÁSICO 1F-T  —  barra relay  (fase A)")
pline("Icc1F", I_1F[0], Ibase, "A")

# =====================================================
# ETAPA 5 — IMPEDÂNCIAS DE THÉVENIN (Z0eq, Z1eq)
# =====================================================
compile_circuit(add_meter=True)
Z0eq, Z1eq = get_thevenin_seq_impedances(RELAY_BUS)

section("IMPEDÂNCIAS DE THÉVENIN  —  barra relay")
for label, Z in (("Z0eq", Z0eq), ("Z1eq", Z1eq)):
    Zpu = Z / Zbase
    print(f"  {label}  :  {Z.real:>+10.6f} {Z.imag:>+10.6f}j Ω"
          f"  |  |Z| = {abs(Z):>10.6f} Ω"
          f"  →  {Zpu.real:>+10.6f} {Zpu.imag:>+10.6f}j pu"
          f"  |  |Z| = {abs(Zpu):.6f} pu")

# =====================================================
# ETAPA 6 — IMPEDÂNCIA SÉRIE DA LINHA (Takagi)
# =====================================================
compile_circuit(add_meter=True)
ZL = get_line_series_impedance(RELAY_LINE)

section(f"IMPEDÂNCIA SÉRIE DA LINHA  {RELAY_LINE}")
ZL_pu = ZL / Zbase
print(f"  ZL  :  {ZL.real:>+10.6f} {ZL.imag:>+10.6f}j Ω"
      f"  |  |ZL| = {abs(ZL):>10.6f} Ω"
      f"  →  {ZL_pu.real:>+10.6f} {ZL_pu.imag:>+10.6f}j pu")
print(f"  Comprimento total da linha : {LINE_LENGTH_MI:.4f} mi")

# =====================================================
# ETAPA 7 — TAKAGI PARA CADA BARRA DE FALTA
# =====================================================
section("LOCALIZADOR DE TAKAGI  —  falta monofásica 1F-T (fase A)")
print(f"  {'Barra':<8} {'d (pu)':>10}  {'d (mi)':>10}  Va_falta no relay")
print(f"  {'-' * W}")

resultados: list[tuple[str, float, float]] = []

for fault_bus in FAULT_BUSES:
    compile_circuit(add_meter=True)
    dss.text(f"New Fault.F1F Bus1={fault_bus}.1.0 Phases=1 R=0.0001")
    dss.solution.solve()

    V_fault = get_bus_voltages(RELAY_BUS)
    I_fault = get_line_currents(RELAY_LINE)

    d = takagi(
        Vs     = V_fault[0],
        Is     = I_fault[0],
        Is_pre = I_pre[0],
        ZL     = ZL,
    )

    if d is not None:
        d_mi  = d * LINE_LENGTH_MI
        v_str = fmt(V_fault[0], Vln, "V")
        print(f"  {fault_bus:<8} {d:>10.6f}  {d_mi:>10.4f}  {v_str}")
        resultados.append((fault_bus, d, d_mi))
    else:
        print(f"  {fault_bus:<8} {'---':>10}  {'---':>10}  denominador nulo")

# =====================================================
# RESUMO FINAL
# =====================================================
section("RESUMO  —  distâncias estimadas")
print(f"  {'Barra falta':<14}  {'d (pu)':>10}  {'d (mi)':>10}")
print(f"  {'-' * 40}")
for bus, d, d_mi in resultados:
    print(f"  {bus:<14}  {d:>10.6f}  {d_mi:>10.4f}")

# =====================================================
# RESTAURA CIRCUITO ORIGINAL
# =====================================================
compile_circuit()
