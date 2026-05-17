"""
takagi.py
---------
Algoritmo de Takagi Modificado para localização de faltas em linhas de
distribuição radiais.

Referências
-----------
Takagi, T. et al. "Development of a new type fault locator using the
one-terminal voltage and current data." IEEE Trans. PAS, 1982.
"""

import numpy as np


def takagi_3ph(Va: complex, Ia: complex, Ia_pre: complex,
               Z1L: complex, L_mi: float) -> float | None:
    """
    Takagi clássico para falta TRIFÁSICA.

    Equação:
        d = Im(Va · ΔIa*) / Im(Z1L · Ia · ΔIa*)

    Parâmetros
    ----------
    Va      : Tensão fase A na barra do relay durante a falta [V].
    Ia      : Corrente fase A na linha durante a falta [A].
    Ia_pre  : Corrente fase A pré-falta [A].
    Z1L     : Impedância de sequência positiva por milha [Ohm/mi].
    L_mi    : (não usado no cálculo — mantido por simetria de assinatura).

    Retorna
    -------
    Distância estimada d [mi], ou None se o denominador for nulo.
    """
    dIa     = Ia - Ia_pre
    dIa_c   = np.conj(dIa)
    num     = np.imag(Va * dIa_c)
    den     = np.imag(Z1L * Ia * dIa_c)
    if np.isclose(den, 0.0):
        return None
    d_pu = num / den          # fração adimensional [0, 1]
    return d_pu * L_mi        # distância em milhas


def takagi_1ph(Va: complex, Iabc: np.ndarray, Iabc_pre: np.ndarray,
               Z1L: complex, Z0L: complex, L_mi: float) -> float | None:
    """
    Takagi MODIFICADO para falta MONOFÁSICA (1F-T), com compensação de
    sequência zero via fator k0.

    Equações
    --------
        k0     = (Z0L - Z1L) / (3 · Z1L)
        I3I0   = Ia + Ib + Ic          (= 3·I0)
        Icomp  = Ia + k0 · I3I0
        d [mi] = Im(Va · ΔIcomp*) / Im(Z1L · Icomp · ΔIcomp*)

    Parâmetros
    ----------
    Va       : Tensão fase A na barra do relay durante a falta [V].
    Iabc     : Array (3,) — correntes trifásicas durante a falta [A].
    Iabc_pre : Array (3,) — correntes trifásicas pré-falta [A].
    Z1L      : Impedância de seq. positiva por milha [Ohm/mi].
    Z0L      : Impedância de seq. zero por milha [Ohm/mi].
    L_mi     : (não usado no cálculo — mantido por simetria de assinatura).

    Retorna
    -------
    Distância estimada d [mi], ou None se o denominador for nulo.
    """
    k0        = (Z0L - Z1L) / (3.0 * Z1L)

    I3I0      = Iabc[0] + Iabc[1] + Iabc[2]
    Icomp     = Iabc[0] + k0 * I3I0

    I3I0_pre  = Iabc_pre[0] + Iabc_pre[1] + Iabc_pre[2]
    Icomp_pre = Iabc_pre[0] + k0 * I3I0_pre

    dIcomp    = Icomp - Icomp_pre
    dIcomp_c  = np.conj(dIcomp)

    num = np.imag(Va * dIcomp_c)
    den = np.imag(Z1L * Icomp * dIcomp_c)
    if np.isclose(den, 0.0):
        return None
    d_pu = num / den          # fração adimensional [0, 1]
    return d_pu * L_mi        # distância em milhas
