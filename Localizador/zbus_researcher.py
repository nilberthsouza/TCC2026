import py_dss_interface
import numpy as np

dss = py_dss_interface.DSS()

dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.solution.solve()

# ===============================
# YBUS -> ZBUS
# ===============================
y_flat = dss.circuit.system_y

y_complex = np.array(y_flat[0::2]) + 1j * np.array(y_flat[1::2])
n = int(np.sqrt(len(y_complex)))

Ybus = y_complex.reshape((n, n))
Zbus = np.linalg.pinv(Ybus)

nodes = dss.circuit.y_node_order

# ===============================
# MATRIZ DE FORTESCUE
# ===============================
a = np.exp(1j * 2 * np.pi / 3)

A = np.array([
    [1, 1, 1],
    [1, a**2, a],
    [1, a, a**2]
], dtype=complex)

Ainv = np.linalg.inv(A)

# ===============================
# EXEMPLO: pegar barra 800 trifásica
# ===============================
barra = "812"

idx = [
    nodes.index(f"{barra}.1"),
    nodes.index(f"{barra}.2"),
    nodes.index(f"{barra}.3"),
]

# bloco 3x3 da barra
Zabc = Zbus[np.ix_(idx, idx)]

print("Zabc:")
print(Zabc)

# converte para sequência
Z012 = Ainv @ Zabc @ A

print("\nZ012:")
print(Z012)

print(f"\nZ0 = {Z012[0,0]}")
print(f"Z1 = {Z012[1,1]}")
print(f"Z2 = {Z012[2,2]}")