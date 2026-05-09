import os
import pathlib
import py_dss_interface
import numpy as np

# ==============================
# CONFIGURAÇÃO
# ==============================
barra = "P1"   # <<< MUDE AQUI (nome da barra)
arquivo_dss = "sistema.dss"

# ==============================
# INICIALIZAÇÃO
# ==============================
script_path = os.path.dirname(os.path.abspath(__file__))
dss_file = pathlib.Path(script_path).joinpath(arquivo_dss)

dss = py_dss_interface.DSS()
dss.text(f"compile [{dss_file}]")

# ==============================
# FUNÇÃO AUXILIAR
# ==============================
def calc_correntes_elemento(nome_elemento):
    dss.circuit.set_active_element(nome_elemento)
    i = dss.cktelement.currents  # [real, imag, real, imag...]

    i_complex = np.array(i[::2]) + 1j * np.array(i[1::2])

    mag = np.abs(i_complex)
    ang = np.angle(i_complex, deg=True)

    return mag, ang

# ==============================
# 1) CURTO TRIFÁSICO
# ==============================
dss.text("clear")
dss.text(f"compile [{dss_file}]")

# cria falta trifásica (3 fases para terra)
dss.text(f"new fault.f3 phases=3 bus1={barra}.1.2.3 bus2=0.0.0 r=0.0001")

dss.text("set mode=snapshot")
dss.text("solve")

mag3, ang3 = calc_correntes_elemento("fault.f3")

# ==============================
# 2) CURTO MONOFÁSICO (fase A-terra)
# ==============================
dss.text("clear")
dss.text(f"compile [{dss_file}]")

# falta monofásica fase 1 (A)
dss.text(f"new fault.f1 phases=1 bus1={barra}.1 bus2=0 r=0.0001")

dss.text("set mode=snapshot")
dss.text("solve")

mag1, ang1 = calc_correntes_elemento("fault.f1")

# ==============================
# RESULTADOS
# ==============================
print("\n==============================")
print(f"RESULTADOS NA BARRA: {barra}")
print("==============================")

print("\n--- Curto Trifásico ---")
for i in range(len(mag3)):
    print(f"Fase {i+1}: |I| = {mag3[i]:.2f} A  |  ang = {ang3[i]:.2f}°")

print("\n--- Curto Monofásico (Fase A) ---")
for i in range(len(mag1)):
    print(f"Condutor {i+1}: |I| = {mag1[i]:.2f} A  |  ang = {ang1[i]:.2f}°")