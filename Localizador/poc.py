import py_dss_interface
import numpy as np

dss = py_dss_interface.DSS()

# =====================================================
# CONSTANTES
# =====================================================
DSS_FILE    = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss"
RELAY_BUS   = "812"
FAULT_LINE  = "Line.L5"
FAULT_BUS   = "850"
Sbase_MVA   = 40.0
Sbase       = Sbase_MVA * 1e6

# Matriz de Fortescue e sua inversa
_a   = np.exp(1j * 2 * np.pi / 3)
A    = np.array([[1,    1,      1    ],
                 [1,    _a**2,  _a   ],
                 [1,    _a,     _a**2]], dtype=complex)
Ainv = np.linalg.inv(A)


# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def compile_circuit(add_meter: bool = False) -> None:
    """Recompila o circuito e opcionalmente adiciona o EnergyMeter."""
    dss.text(f"compile {DSS_FILE}")
    if add_meter:
        dss.text(f"New EnergyMeter.M1 Element={FAULT_LINE} Terminal=1")
    dss.solution.solve()


def polar_to_complex(mag: float, ang_deg: float) -> complex:
    """Converte magnitude + ângulo (graus) para número complexo via NumPy."""
    ang_rad = np.deg2rad(ang_deg)
    return mag * (np.cos(ang_rad) + 1j * np.sin(ang_rad))


def get_bus_voltages(bus: str, n_phases: int = 3) -> np.ndarray:
    """
    Retorna array complexo de tensões de fase na barra informada.
    Shape: (n_phases,)
    """
    dss.circuit.set_active_bus(bus)
    v = dss.bus.vmag_angle
    return np.array(
        [polar_to_complex(v[2*k], v[2*k + 1]) for k in range(n_phases)],
        dtype=complex
    )


def get_line_currents(element: str, terminal: int = 2, n_phases: int = 3) -> np.ndarray:
    """
    Retorna array complexo de correntes no terminal indicado do elemento.
    terminal=1 → índices 0-5; terminal=2 → índices 6-11.
    Shape: (n_phases,)
    """
    dss.circuit.set_active_element(element)
    curr = dss.cktelement.currents_mag_ang
    offset = (terminal - 1) * 2 * n_phases
    return np.array(
        [polar_to_complex(curr[offset + 2*k], curr[offset + 2*k + 1])
         for k in range(n_phases)],
        dtype=complex
    )


def abc_to_012(Vabc: np.ndarray) -> np.ndarray:
    """Transforma vetor de fase (ABC) em componentes de sequência (012)."""
    return Ainv @ Vabc


def compute_bases(bus: str) -> tuple[float, float, float, float]:
    """
    Calcula bases do sistema a partir da tensão base da barra.
    Retorna: (Vbase_ln, Vbase_ll, Ibase, Zbase) em V / A / Ω.
    """
    dss.circuit.set_active_bus(bus)
    Vbase_ln = dss.bus.kv_base * 1e3
    Vbase_ll = Vbase_ln * np.sqrt(3)
    Ibase    = Sbase / (np.sqrt(3) * Vbase_ll)
    Zbase    = Vbase_ll**2 / Sbase
    return Vbase_ln, Vbase_ll, Ibase, Zbase


def compute_thevenin_impedances(relay_bus: str, Zbase: float) -> tuple[complex, complex, complex]:
    """
    Calcula as impedâncias de Thévenin de sequência (Z0, Z1, Z2)
    na barra relay_bus a partir da Zbus (pinv da Ybus).
    Retorna: (Zth0, Zth1, Zth2) em Ω.
    """
    y_flat    = dss.circuit.system_y
    y_complex = np.array(y_flat[0::2]) + 1j * np.array(y_flat[1::2])
    n         = int(np.sqrt(len(y_complex)))
    Ybus      = y_complex.reshape((n, n))
    Zbus      = np.linalg.pinv(Ybus)

    nodes = dss.circuit.y_node_order
    idx   = [
        nodes.index(f"{relay_bus}.1"),
        nodes.index(f"{relay_bus}.2"),
        nodes.index(f"{relay_bus}.3"),
    ]

    Zabc = Zbus[np.ix_(idx, idx)]
    Z012 = Ainv @ Zabc @ A

    return Z012[0, 0], Z012[1, 1], Z012[2, 2]


def print_phase_a(label: str, value: complex, base: float, real_unit: str = "V") -> None:
    """
    Imprime magnitude e ângulo da fase A em unidades reais e em pu.
    real_unit: unidade física do valor real (ex: 'V', 'A', 'Ω').
    """
    val_pu  = value / base
    mag     = abs(value)
    mag_pu  = abs(val_pu)
    ang_deg = np.degrees(np.angle(value))
    print(f"  [{label}]  Fase A:"
          f"  {mag:.4f} {real_unit} ∠ {ang_deg:.2f}°"
          f"  |  {mag_pu:.6f} pu ∠ {ang_deg:.2f}°"
          f"  ({value.real:+.4f}{value.imag:+.4f}j {real_unit})")


# =====================================================
# COMPILAÇÃO E BASES
# =====================================================
compile_circuit()
Vbase_ln, Vbase_ll, Ibase, Zbase = compute_bases(RELAY_BUS)

print("================ BASES DO SISTEMA ================")
print(f"  Vbase (LN): {Vbase_ln:.2f} V")
print(f"  Vbase (LL): {Vbase_ll:.2f} V")
print(f"  Sbase:      {Sbase:.2f} VA")
print(f"  Ibase:      {Ibase:.4f} A")
print(f"  Zbase:      {Zbase:.6f} Ω")

# =====================================================
# PRÉ-FALTA
# =====================================================
V_prefault = get_bus_voltages(RELAY_BUS)     # (3,) complex  [V]
I_prefault = get_line_currents(FAULT_LINE)   # (3,) complex  [A]

print("\n================ PRÉ-FALTA (fase A) ================")
print_phase_a("tensão",   V_prefault[0], Vbase_ln, real_unit="V")
print_phase_a("corrente", I_prefault[0], Ibase,    real_unit="A")

# =====================================================
# CURTO-CIRCUITO TRIFÁSICO (3F)
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F3F Bus1={RELAY_BUS} Phases=3 R=0.0001")
dss.solution.solve()

I_cc3f = get_line_currents(FAULT_LINE)

print("\n================ CURTO TRIFÁSICO — fase A ================")
print_phase_a("Icc3F", I_cc3f[0], Ibase, real_unit="A")

# =====================================================
# CURTO-CIRCUITO MONOFÁSICO (1F-T) — fase A
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F1F Bus1={RELAY_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

I_cc1f = get_line_currents(FAULT_LINE)

print("\n================ CURTO MONOFÁSICO — fase A ================")
print_phase_a("Icc1F", I_cc1f[0], Ibase, real_unit="A")

# =====================================================
# IMPEDÂNCIAS DE THÉVENIN (sequências)
# =====================================================
compile_circuit(add_meter=True)
Zth0, Zth1, Zth2 = compute_thevenin_impedances(RELAY_BUS, Zbase)

print("\n================ IMPEDÂNCIAS DE THÉVENIN ================")
for label, Z in (("Zth0", Zth0), ("Zth1", Zth1), ("Zth2", Zth2)):
    Zpu = Z / Zbase
    print(f"  {label}: {Z.real:+.6f} {Z.imag:+.6f}j Ω"
          f"  →  {Zpu.real:+.6f} {Zpu.imag:+.6f}j pu"
          f"  |  |Z| = {abs(Zpu):.6f} pu")

# =====================================================
# FALTA MONOFÁSICA NA BARRA fault_location
# =====================================================
compile_circuit(add_meter=True)
dss.text(f"New Fault.F1F Bus1={FAULT_BUS}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

V_fault = get_bus_voltages(RELAY_BUS)
I_fault = get_line_currents(FAULT_LINE)

print(f"\n================ PÓS-FALTA em {FAULT_BUS} — fase A ================")
print_phase_a("tensão",   V_fault[0], Vbase_ln, real_unit="V")
print_phase_a("corrente", I_fault[0], Ibase,    real_unit="A")

# =====================================================
# COMPONENTES SIMÉTRICAS DA CORRENTE
# =====================================================
I012 = abc_to_012(I_fault)        # (3,) → [I0, I1, I2]
If0, If1, If2 = I012

print("\n================ COMPONENTES SIMÉTRICAS DA CORRENTE — fase A ================")
for label, I in (("If0", If0), ("If1", If1), ("If2", If2)):
    print_phase_a(label, I, Ibase, real_unit="A")

# =====================================================
# TENSÃO DE THÉVENIN (pré-falta fase A)
# =====================================================
Vth    = V_prefault[0]           # tensão pré-falta fase A no relay
Vth_pu = Vth / Vbase_ln

# =====================================================
# TENSÕES DE SEQUÊNCIA NO RELAY (modelo)
# =====================================================
Vs1 = Vth  - If1 * Zth1
Vs2 =      - If2 * Zth2
Vs0 =      - If0 * Zth0

print("\n================ TENSÕES DE SEQUÊNCIA NO RELAY (modelo) ================")
for label, V in (("Vs1", Vs1), ("Vs2", Vs2), ("Vs0", Vs0)):
    print_phase_a(label, V, Vbase_ln, real_unit="V")

# =====================================================
# V_MONITOR = Vs1 + Vs2 + Vs0
# =====================================================
V_monitor    = Vs1 + Vs2 + Vs0
V_monitor_pu = V_monitor / Vbase_ln

V_relay_pu   = V_fault[0] / Vbase_ln
erro_mag     = abs(abs(V_monitor_pu) - abs(V_relay_pu))
erro_ang     = abs(np.degrees(np.angle(V_monitor_pu)) - np.degrees(np.angle(V_relay_pu)))

print("\n================ V_MONITOR vs V_RELAY (OpenDSS) ================")
print_phase_a("V_relay  OpenDSS", V_fault[0],  Vbase_ln, real_unit="V")
print_phase_a("V_monitor modelo", V_monitor,   Vbase_ln, real_unit="V")
print(f"\n  Erro magnitude: {erro_mag:.6f} pu  ({erro_mag*100:.4f}%)")
print(f"  Erro ângulo:    {erro_ang:.4f}°")

# =====================================================
# RESTAURA CIRCUITO ORIGINAL
# =====================================================
compile_circuit()