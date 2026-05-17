"""
circuit_utils.py
----------------
Funções utilitárias relacionadas ao circuito OpenDSS:
tensões de barra, correntes de linha, bases do sistema e
impedâncias de Thévenin via Ybus.
"""

import numpy as np

# Operador de Fortescue e sua inversa
_a   = np.exp(1j * 2 * np.pi / 3)
A    = np.array([[1,    1,      1    ],
                 [1,    _a**2,  _a   ],
                 [1,    _a,     _a**2]], dtype=complex)
Ainv = np.linalg.inv(A)


def polar_to_rect(mag: float, ang_deg: float) -> complex:
    """Magnitude + ângulo (graus) -> número complexo."""
    ang = np.deg2rad(ang_deg)
    return mag * (np.cos(ang) + 1j * np.sin(ang))


def compile_circuit(dss, dss_file: str, relay_line: str,
                    add_meter: bool = False) -> None:
    """Recompila o circuito base e opcionalmente adiciona EnergyMeter."""
    dss.text(f"compile {dss_file}")
    if add_meter:
        dss.text(f"New EnergyMeter.M1 Element={relay_line} Terminal=1")
    dss.solution.solve()


def get_bus_voltages(dss, bus: str, n_phases: int = 3) -> np.ndarray:
    """Array complexo (n_phases,) das tensões de fase na barra."""
    dss.circuit.set_active_bus(bus)
    v = dss.bus.vmag_angle
    return np.array([polar_to_rect(v[2*k], v[2*k+1]) for k in range(n_phases)],
                    dtype=complex)


def get_line_currents(dss, element: str, terminal: int = 1,
                      n_phases: int = 3) -> np.ndarray:
    """
    Array complexo (n_phases,) das correntes no terminal indicado.
    terminal=1 -> offset 0 (relay side, sentido físico correto).
    terminal=2 -> offset n_phases*2 (EVITAR: aparece defasado ~180 graus).
    """
    dss.circuit.set_active_element(element)
    curr   = dss.cktelement.currents_mag_ang
    offset = (terminal - 1) * 2 * n_phases
    return np.array([polar_to_rect(curr[offset + 2*k], curr[offset + 2*k+1])
                     for k in range(n_phases)], dtype=complex)


def compute_bases(dss, bus: str,
                  sbase: float) -> tuple[float, float, float, float]:
    """
    Bases do sistema na barra informada.
    Retorna (Vbase_ln [V], Vbase_ll [V], Ibase [A], Zbase [Ohm]).
    """
    dss.circuit.set_active_bus(bus)
    Vln   = dss.bus.kv_base * 1e3
    Vll   = Vln * np.sqrt(3)
    Ibase = sbase / (np.sqrt(3) * Vll)
    Zbase = Vll**2 / sbase
    return Vln, Vll, Ibase, Zbase


def get_thevenin_seq_impedances(dss, bus: str) -> tuple[complex, complex]:
    """
    Z0eq e Z1eq de Thévenin na barra via Zbus = pinv(Ybus).
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
