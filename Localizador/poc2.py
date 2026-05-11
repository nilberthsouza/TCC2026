import py_dss_interface
import numpy as np

dss = py_dss_interface.DSS()

# =====================================================
# CONFIGURAÇÕES
# =====================================================
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


def get_line_impedance_per_mile(element: str) -> complex:
    """
    Retorna a impedância de sequência positiva por milha da linha (Ω/mi).
    O Takagi recebe esta grandeza como ZL, e seu resultado d já sai em milhas.
    """
    line_name = element.split(".")[-1]
    dss.lines.name = line_name
    r1 = dss.lines.r1      # Ω/unidade-de-comprimento
    x1 = dss.lines.x1      # Ω/unidade-de-comprimento
    # r1/x1 estão por milha quando o circuito usa milhas — retorna direto
    return complex(r1, x1)


def get_line_total_impedance(element: str) -> complex:
    """
    Retorna a impedância série total da linha (Ω):
      ZL_total = (R1 + jX1) * length
    """
    line_name = element.split(".")[-1]
    dss.lines.name = line_name
    r1     = dss.lines.r1
    x1     = dss.lines.x1
    length = dss.lines.length
    return complex(r1 * length, x1 * length)

def takagi(Vs: complex, Is: complex, Is_pre: complex, ZL_per_mi: complex) -> float | None:
    """
    Distância da falta em milhas pelo método de Takagi.

    A fórmula canônica é:
      d = Im(Vs · ΔIs*) / Im(ZL · Is · ΔIs*)

    Quando ZL é dado em Ω/mi, d sai diretamente em milhas.
    A corrente Is deve fluir no sentido relay → falta (positivo para a frente).

    Retorna None se o denominador for nulo.
    """
    dI      = Is - Is_pre
    dI_conj = np.conj(dI)
    num     = np.imag(Vs * dI_conj)
    den     = np.imag(ZL_per_mi * Is * dI_conj)
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
# ETAPA 6 — IMPEDÂNCIA DA LINHA (Takagi usa Ω/mi)
# =====================================================
compile_circuit(add_meter=True)
ZL_per_mi   = get_line_impedance_per_mile(RELAY_LINE)
ZL_total    = get_line_total_impedance(RELAY_LINE)

section(f"IMPEDÂNCIA DA LINHA  {RELAY_LINE}")
ZL_total_pu = ZL_total / Zbase
ZL_mi_pu    = ZL_per_mi / Zbase
print(f"  ZL total  :  {ZL_total.real:>+10.6f} {ZL_total.imag:>+10.6f}j Ω"
      f"  →  {ZL_total_pu.real:>+10.6f} {ZL_total_pu.imag:>+10.6f}j pu")
print(f"  ZL/mi     :  {ZL_per_mi.real:>+10.6f} {ZL_per_mi.imag:>+10.6f}j Ω/mi"
      f"  →  {ZL_mi_pu.real:>+10.6f} {ZL_mi_pu.imag:>+10.6f}j pu/mi")
print(f"  Comprimento da linha {RELAY_LINE}  : {dss.lines.length:.4f} mi")


# =====================================================
# DIAGNÓSTICO — inspeciona valores brutos da linha
# =====================================================
print("\n[DIAG] Valores brutos dss.lines para", RELAY_LINE)
line_name = RELAY_LINE.split(".")[-1]
dss.lines.name = line_name
print(f"  r1          = {dss.lines.r1}")
print(f"  x1          = {dss.lines.x1}")
print(f"  r0          = {dss.lines.r0}")
print(f"  x0          = {dss.lines.x0}")
print(f"  length      = {dss.lines.length}")
print(f"  units       = {dss.lines.units}")   # 0=none,1=mi,2=kft,3=km,4=m,5=ft,6=in,7=cm
print(f"  normamps    = {dss.lines.norm_amps}")
# Rmatrix e Xmatrix (por milha, sequência de fase)
try:
    print(f"  rmatrix     = {dss.lines.rmatrix}")
    print(f"  xmatrix     = {dss.lines.xmatrix}")
except Exception as e:
    print(f"  rmatrix/xmatrix: {e}")
# Verifica ZL implícita: se ZL_total = r1*length, qual comprimento faz sentido?
r1 = dss.lines.r1; x1 = dss.lines.x1; length = dss.lines.length
print(f"\n  ZL_per_mi (r1, x1)        = {r1:.6f} + {x1:.6f}j Ω/mi")
print(f"  ZL_total  (r1*len,x1*len) = {r1*length:.6f} + {x1*length:.6f}j Ω")
print(f"  Se ZL/mi esperada ~0.289+0.600j → ratio r1: {r1/0.289:.4f}, x1: {x1/0.600:.4f}")
# Distâncias reais de referência: 850=0.62mi → ZL esperada = 0.62 * ZL/mi
# Os erros foram ~2x → ZL/mi atual pode estar dobrada
print(f"\n  Fator de escala implícito nos erros: ~{1.4385/0.620:.4f}x (850)")
print(f"  Ou seja, ZL efetiva usada é {1.4385/0.620:.4f}x maior que deveria")

# =====================================================
# ETAPA 7 — TAKAGI PARA CADA BARRA DE FALTA
# =====================================================
# Sinal da corrente: terminal 2 da linha, sentido convencional OpenDSS é
# positivo entrando na barra 812. Takagi precisa da corrente saindo do relay
# em direção à falta, então negamos Is (inversão de sentido).
section("LOCALIZADOR DE TAKAGI  —  falta monofásica 1F-T (fase A)")
print(f"  {'Barra':<8} {'d (mi)':>10}  Va_falta no relay")
print(f"  {'-' * W}")

resultados: list[tuple[str, float]] = []

for fault_bus in FAULT_BUSES:
    compile_circuit(add_meter=True)
    dss.text(f"New Fault.F1F Bus1={fault_bus}.1.0 Phases=1 R=0.0001")
    dss.solution.solve()

    V_fault = get_bus_voltages(RELAY_BUS)
    I_fault = get_line_currents(RELAY_LINE)

    # Corrente medida no terminal 2 (barra 812) entra na barra → negamos
    # para obter sentido relay → falta, conforme convenção do Takagi
    Is_fwd     = -I_fault[0]
    Is_pre_fwd = -I_pre[0]

    d_mi = takagi(
        Vs        = V_fault[0],
        Is        = Is_fwd,
        Is_pre    = Is_pre_fwd,
        ZL_per_mi = ZL_per_mi,
    )

    if d_mi is not None:
        v_str = fmt(V_fault[0], Vln, "V")
        print(f"  {fault_bus:<8} {d_mi:>10.4f}  {v_str}")
        resultados.append((fault_bus, d_mi))
    else:
        print(f"  {fault_bus:<8} {'---':>10}  denominador nulo")

# =====================================================
# RESUMO FINAL
# =====================================================
section("RESUMO  —  distâncias estimadas (Takagi)")
print(f"  {'Barra falta':<14}  {'d estimado (mi)':>16}  {'Referência (mi)':>16}")
print(f"  {'-' * 52}")
ref = {"850": 0.620, "854": 2.180, "822": 3.000, "834": 4.050, "840": 6.750, "848": 7.470}
for bus, d_mi in resultados:
    ref_val = ref.get(bus, float("nan"))
    erro    = abs(d_mi - ref_val)
    print(f"  {bus:<14}  {d_mi:>16.4f}  {ref_val:>16.3f}  (erro: {erro:.4f} mi)")

# =====================================================
# RESTAURA CIRCUITO ORIGINAL
# =====================================================
compile_circuit()
