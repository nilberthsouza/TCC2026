"""
linecode_utils.py
-----------------
Funções utilitárias para leitura de parâmetros de linecodes do OpenDSS.
"""


def get_linecode_params(dss, linecode_name: str) -> tuple[float, float, float, float]:
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
