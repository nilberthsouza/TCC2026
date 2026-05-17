"""
display_utils.py
----------------
Funções auxiliares de formatação e impressão de resultados.
"""

import numpy as np

W = 72  # largura padrão das seções


def section(title: str) -> None:
    """Imprime cabeçalho de seção."""
    print(f"\n{'=' * W}")
    print(f"  {title}")
    print(f"{'=' * W}")


def fmt(val: complex, base: float, unit: str) -> str:
    """Formata valor complexo com magnitude, ângulo, parte real/imag e pu."""
    mag    = abs(val)
    ang    = np.degrees(np.angle(val))
    mag_pu = mag / base
    return (f"{mag:>12.4f} {unit} angle {ang:>+7.2f} deg  "
            f"({val.real:>+10.4f}{val.imag:>+10.4f}j)  "
            f"-> {mag_pu:.6f} pu")


def pline(label: str, val: complex, base: float, unit: str) -> None:
    """Imprime uma linha formatada de fasor."""
    print(f"  {label:<20} {fmt(val, base, unit)}")


def fmt_z(Z: complex, Zbase: float) -> str:
    """Formata impedância com magnitude em Ohm, ângulo e pu."""
    return (f"{abs(Z):>10.6f} Ohm  ∠{np.degrees(np.angle(Z)):>+8.3f}°"
            f"  ({abs(Z)/Zbase:.6f} pu)")


def print_bases(relay_bus: str, relay_line: str, sbase_mva: float,
                vln: float, vll: float, ibase: float, zbase: float) -> None:
    section("BASES DO SISTEMA")
    print(f"  Relay bus          : {relay_bus}")
    print(f"  Linha monitorada   : {relay_line}")
    print(f"  Vbase fase-neutro  : {vln:.2f} V")
    print(f"  Vbase fase-fase    : {vll:.2f} V")
    print(f"  Sbase              : {sbase_mva:.1f} MVA")
    print(f"  Ibase              : {ibase:.4f} A")
    print(f"  Zbase              : {zbase:.6f} Ohm")


def print_linecode(linecode_name: str, r1: float, x1: float,
                   r0: float, x0: float) -> None:
    Z1 = complex(r1, x1)
    Z0 = complex(r0, x0)
    section(f"LINECODE DE REFERÊNCIA  —  {linecode_name}")
    print(f"  r1  : {r1:.6f} Ohm/mi")
    print(f"  x1  : {x1:.6f} Ohm/mi")
    print(f"  r0  : {r0:.6f} Ohm/mi")
    print(f"  x0  : {x0:.6f} Ohm/mi")
    print(f"  |Z1|: {abs(Z1):.6f} Ohm/mi")
    print(f"  |Z0|: {abs(Z0):.6f} Ohm/mi")


def print_thevenin(Z0eq: complex, Z1eq: complex, zbase: float) -> None:
    section("IMPEDÂNCIAS DE THÉVENIN  —  barra relay")
    for label, Z in (("Z0eq", Z0eq), ("Z1eq", Z1eq)):
        Zpu = Z / zbase
        print(f"  {label}  :  {Z.real:>+10.6f} {Z.imag:>+10.6f}j Ohm"
              f"  |  |Z| = {abs(Z):>10.6f} Ohm"
              f"  ->  {Zpu.real:>+10.6f} {Zpu.imag:>+10.6f}j pu"
              f"  |  |Z| = {abs(Zpu):.6f} pu")


def print_debug_1ph(fault_bus: str, ref_dist: float,
                    Z1L: complex, Z0L: complex,
                    Va_f: complex, V_pre_a: complex,
                    Iabc_fault: np.ndarray, Iabc_pre: np.ndarray,
                    I3I0_f: complex, I3I0_p: complex,
                    Icomp_f: complex, Icomp_p: complex,
                    dIcomp: complex, num: float, den: float,
                    d_mi: float) -> None:
    section(f"DEBUG — barra {fault_bus}  (ref={ref_dist} mi)")
    print(f"  Z1L          : {abs(Z1L):.6f} Ohm  angle {np.degrees(np.angle(Z1L)):>+.3f} deg")
    print(f"  Z0L          : {abs(Z0L):.6f} Ohm  angle {np.degrees(np.angle(Z0L)):>+.3f} deg")
    k0 = (Z0L - Z1L) / (3.0 * Z1L)
    print(f"  k0           : {k0.real:>+.6f}{k0.imag:>+.6f}j")
    print()
    print(f"  Va (falta)   : {abs(Va_f):>12.4f} V  angle {np.degrees(np.angle(Va_f)):>+.3f} deg")
    print(f"  Va (pre)     : {abs(V_pre_a):>12.4f} V  angle {np.degrees(np.angle(V_pre_a)):>+.3f} deg")
    print()
    for ph, lbl in enumerate(["A", "B", "C"]):
        print(f"  I_fault fase {lbl}: {abs(Iabc_fault[ph]):>10.4f} A  "
              f"angle {np.degrees(np.angle(Iabc_fault[ph])):>+.3f} deg")
    print()
    for ph, lbl in enumerate(["A", "B", "C"]):
        print(f"  I_pre   fase {lbl}: {abs(Iabc_pre[ph]):>10.4f} A  "
              f"angle {np.degrees(np.angle(Iabc_pre[ph])):>+.3f} deg")
    print()
    print(f"  I3I0 (falta) : {abs(I3I0_f):>10.4f} A  angle {np.degrees(np.angle(I3I0_f)):>+.3f} deg")
    print(f"  I3I0 (pre)   : {abs(I3I0_p):>10.4f} A  angle {np.degrees(np.angle(I3I0_p)):>+.3f} deg")
    print(f"  Icomp (falta): {abs(Icomp_f):>10.4f} A  angle {np.degrees(np.angle(Icomp_f)):>+.3f} deg")
    print(f"  Icomp (pre)  : {abs(Icomp_p):>10.4f} A  angle {np.degrees(np.angle(Icomp_p)):>+.3f} deg")
    print(f"  dIcomp       : {abs(dIcomp):>10.4f} A  angle {np.degrees(np.angle(dIcomp)):>+.3f} deg")
    print()
    print(f"  numerador    : Im(Va * dIcomp*)             = {num:>+.6f}  [V*A]")
    print(f"  denominador  : Im(z1_mi * Icomp * dIcomp*)  = {den:>+.6f}  [Ohm/mi * A^2]")
    print(f"  d_mi         : num/den = {d_mi:>+.6f} mi  (esperado: {ref_dist} mi)")
    print()
