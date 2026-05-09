import py_dss_interface
import math

dss = py_dss_interface.DSS()

# =====================================================
# COMPILA E RESOLVE
# =====================================================
dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.solution.solve()

# =====================================================
# BASES DO SISTEMA
# =====================================================
Sbase_MVA = 40.0
Sbase = Sbase_MVA * 1e6           # VA
relay_position = "812"

dss.circuit.set_active_bus(relay_position)


print("Barra ativa:", dss.bus.name)

kv_base_ln = dss.bus.kv_base      # kV fase-neutro
Vbase = kv_base_ln * 1000         # V fase-neutro

Vbase_ll = Vbase * math.sqrt(3)   # tensão linha-linha

Ibase = Sbase / (math.sqrt(3) * Vbase_ll)
Zbase = (Vbase_ll ** 2) / Sbase

print("\n================ BASES DO SISTEMA ================")
print(f"Vbase (LN): {Vbase:.2f} V")
print(f"Vbase (LL): {Vbase_ll:.2f} V")
print(f"Sbase:      {Sbase:.2f} VA")
print(f"Ibase:      {Ibase:.4f} A")
print(f"Zbase:      {Zbase:.6f} ohms")

# =====================================================
# TENSÕES PRÉ-FALTA
# =====================================================
v = dss.bus.vmag_angle

# vetor para armazenar tensões reais
tensoes_prefalta_reais = []

print("\n================ TENSÕES PRÉ-FALTA ================")

for i in range(0, len(v), 2):
    mag_v = v[i]
    ang = v[i + 1]

    tensoes_prefalta_reais.append((mag_v, ang))

    mag_pu = mag_v / Vbase
    fase = i // 2 + 1

    print(f"Fase {fase}: {mag_pu:.4f} pu ∠ {ang:.2f}°")

print("\nVetor tensões reais:")
print(tensoes_prefalta_reais)

# =====================================================
# CORRENTES PRÉ-FALTA
# =====================================================
dss.circuit.set_active_element("Line.L5")
curr = dss.cktelement.currents_mag_ang

# lado da barra 812 = terminal 2
correntes_prefalta_reais = []

print("\n================ CORRENTES PRÉ-FALTA ================")

for i in range(6, 12, 2):   # terminal 2
    mag = curr[i]
    ang = curr[i + 1]

    correntes_prefalta_reais.append((mag, ang))

    mag_pu = mag / Ibase
    fase = ((i - 6) // 2) + 1

    print(f"Fase {fase}: {mag_pu:.4f} pu ∠ {ang:.2f}°")

print("\nVetor correntes reais:")
print(correntes_prefalta_reais)

# =====================================================
# ADICIONA ENERGYMETER (necessário para zonas de falta)
# =====================================================
dss.text("New EnergyMeter.M1 Element=Line.L5 Terminal=1")
dss.solution.solve()

# =====================================================
# CURTO-CIRCUITO TRIFÁSICO (3F)
# =====================================================
dss.text(f"New Fault.F3F Bus1={relay_position} Phases=3 R=0.0001")
dss.solution.solve()

dss.circuit.set_active_element("Line.L5")
curr_cc3f = dss.cktelement.currents_mag_ang

correntes_cc3f_reais = []
print("\n================ CURTO-CIRCUITO TRIFÁSICO (3F) ================")
for i in range(6, 12, 2):
    mag = curr_cc3f[i]
    ang = curr_cc3f[i + 1]
    correntes_cc3f_reais.append((mag, ang))
    mag_pu = mag / Ibase
    fase = ((i - 6) // 2) + 1
    print(f"Fase {fase}: {mag_pu:.4f} pu ∠ {ang:.2f}°  |  {mag:.4f} A ∠ {ang:.2f}°")

print("\nVetor correntes reais CC3F (A):")
print(correntes_cc3f_reais)

# Recompila para limpar a falta antes do próximo curto
dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.text("New EnergyMeter.M1 Element=Line.L5 Terminal=1")
dss.solution.solve()

# =====================================================
# CURTO-CIRCUITO MONOFÁSICO (1F-T) — fase A com terra
# =====================================================
dss.text(f"New Fault.F1F Bus1={relay_position}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

dss.circuit.set_active_element("Line.L5")
curr_cc1f = dss.cktelement.currents_mag_ang

correntes_cc1f_reais = []
print("\n================ CURTO-CIRCUITO MONOFÁSICO (1F-T) ================")
for i in range(6, 12, 2):
    mag = curr_cc1f[i]
    ang = curr_cc1f[i + 1]
    correntes_cc1f_reais.append((mag, ang))
    mag_pu = mag / Ibase
    fase = ((i - 6) // 2) + 1
    print(f"Fase {fase}: {mag_pu:.4f} pu ∠ {ang:.2f}°  |  {mag:.4f} A ∠ {ang:.2f}°")

print("\nVetor correntes reais CC1F (A):")
print(correntes_cc1f_reais)

# Recompila para restaurar o circuito original
dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.solution.solve()


print("\n================ print faltas (pu) ================")
print(f"{'Fase':<6} {'|Icc3F| (pu)':<16} {'∠ 3F (°)':<14} {'|Icc1F| (pu)':<16} {'∠ 1F (°)'}")
print("-" * 68)
for i in range(3):
    mag3f_pu = correntes_cc3f_reais[i][0] / Ibase
    ang3f    = correntes_cc3f_reais[i][1]
    mag1f_pu = correntes_cc1f_reais[i][0] / Ibase
    ang1f    = correntes_cc1f_reais[i][1]
    print(f"{i+1:<6} {mag3f_pu:<16.4f} {ang3f:<14.2f} {mag1f_pu:<16.4f} {ang1f:.2f}")

# =====================================================
# IMPEDÂNCIAS DE THÉVENIN VIA ZBUS (sequências 0, 1, 2)
# =====================================================
import numpy as np

# Monta Ybus e inverte para Zbus
y_flat    = dss.circuit.system_y
y_complex = np.array(y_flat[0::2]) + 1j * np.array(y_flat[1::2])
n         = int(np.sqrt(len(y_complex)))
Ybus      = y_complex.reshape((n, n))
Zbus      = np.linalg.pinv(Ybus)

nodes = dss.circuit.y_node_order

# Matriz de Fortescue
a    = np.exp(1j * 2 * np.pi / 3)
A    = np.array([[1, 1, 1],
                 [1, a**2, a],
                 [1, a,    a**2]], dtype=complex)
Ainv = np.linalg.inv(A)

# Índices da barra 812 (fases 1, 2, 3)
idx = [
    nodes.index(f"{relay_position}.1"),
    nodes.index(f"{relay_position}.2"),
    nodes.index(f"{relay_position}.3"),
]

# Bloco 3x3 da barra 812 em coordenadas de fase
Zabc = Zbus[np.ix_(idx, idx)]

# Converte para componentes de sequência
Z012 = Ainv @ Zabc @ A

Zth0 = Z012[0, 0]   # sequência zero
Zth1 = Z012[1, 1]   # sequência positiva
Zth2 = Z012[2, 2]   # sequência negativa

# Em pu
Zth0_pu = Zth0 / Zbase
Zth1_pu = Zth1 / Zbase
Zth2_pu = Zth2 / Zbase

# Vetor com valores reais para conferência
thevenin_reais = {
    "Zabc":    Zabc,
    "Z012":    Z012,
    "Zth0_ohm": Zth0,
    "Zth1_ohm": Zth1,
    "Zth2_ohm": Zth2,
    "Zth0_pu":  Zth0_pu,
    "Zth1_pu":  Zth1_pu,
    "Zth2_pu":  Zth2_pu,
}

print("\n================ ZABC (bloco 3x3 barra 812) ================")
print(Zabc)

print("\n================ Z012 (sequências) ================")
print(Z012)

print("\n================ IMPEDÂNCIAS DE THÉVENIN ================")
print(f"Zth0: {Zth0.real:+.6f} {Zth0.imag:+.6f}j ohms  |  |Zth0| = {abs(Zth0):.6f} ohms")
print(f"Zth1: {Zth1.real:+.6f} {Zth1.imag:+.6f}j ohms  |  |Zth1| = {abs(Zth1):.6f} ohms")
print(f"Zth2: {Zth2.real:+.6f} {Zth2.imag:+.6f}j ohms  |  |Zth2| = {abs(Zth2):.6f} ohms")

print(f"\nZth0: {Zth0_pu.real:+.6f} {Zth0_pu.imag:+.6f}j pu  |  |Zth0| = {abs(Zth0_pu):.6f} pu")
print(f"Zth1: {Zth1_pu.real:+.6f} {Zth1_pu.imag:+.6f}j pu  |  |Zth1| = {abs(Zth1_pu):.6f} pu")
print(f"Zth2: {Zth2_pu.real:+.6f} {Zth2_pu.imag:+.6f}j pu  |  |Zth2| = {abs(Zth2_pu):.6f} pu")

print("\nVetor Thévenin completo:")
print(thevenin_reais)

# =====================================================
# FALTA MONOFÁSICA NA BARRA fault_location
# =====================================================
fault_location = "850"

# Recompila para garantir circuito limpo sem faltas anteriores
dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.text("New EnergyMeter.M1 Element=Line.L5 Terminal=1")
dss.solution.solve()

dss.text(f"New Fault.F1F Bus1={fault_location}.1.0 Phases=1 R=0.0001")
dss.solution.solve()

# --- Tensões na barra relay_position ---
dss.circuit.set_active_bus(relay_position)
v_falta = dss.bus.vmag_angle

tensoes_falta_reais = []
print("\n================ TENSÕES PÓS-FALTA (relay_position) ================")
for i in range(0, 6, 2):
    mag = v_falta[i]
    ang = v_falta[i + 1]
    tensoes_falta_reais.append((mag, ang))
    print(f"Fase {i//2+1}: {mag/Vbase:.6f} pu ∠ {ang:.2f}°")

# --- Correntes na Line.L5 (relay_position) ---
dss.circuit.set_active_element("Line.L5")
curr_falta = dss.cktelement.currents_mag_ang

correntes_falta_reais = []
print("\n================ CORRENTES PÓS-FALTA (relay_position) ================")
for i in range(6, 12, 2):
    mag = curr_falta[i]
    ang = curr_falta[i + 1]
    correntes_falta_reais.append((mag, ang))
    print(f"Fase {((i-6)//2)+1}: {mag/Ibase:.6f} pu ∠ {ang:.2f}°")

print("\nVetor correntes reais pós-falta (A):")
print(correntes_falta_reais)

# =====================================================
# COMPONENTES SIMÉTRICAS DA CORRENTE (Fortescue)
# =====================================================
Iabc = np.array([
    complex(correntes_falta_reais[0][0] * math.cos(math.radians(correntes_falta_reais[0][1])),
            correntes_falta_reais[0][0] * math.sin(math.radians(correntes_falta_reais[0][1]))),
    complex(correntes_falta_reais[1][0] * math.cos(math.radians(correntes_falta_reais[1][1])),
            correntes_falta_reais[1][0] * math.sin(math.radians(correntes_falta_reais[1][1]))),
    complex(correntes_falta_reais[2][0] * math.cos(math.radians(correntes_falta_reais[2][1])),
            correntes_falta_reais[2][0] * math.sin(math.radians(correntes_falta_reais[2][1]))),
], dtype=complex)

I012 = Ainv @ Iabc
If0 = I012[0]
If1 = I012[1]
If2 = I012[2]

print("\n================ COMPONENTES SIMÉTRICAS DA CORRENTE (pu) ================")
print(f"If0: {(If0/Ibase).real:+.6f} {(If0/Ibase).imag:+.6f}j pu  |  |If0| = {abs(If0)/Ibase:.6f} pu ∠ {math.degrees(np.angle(If0)):.2f}°")
print(f"If1: {(If1/Ibase).real:+.6f} {(If1/Ibase).imag:+.6f}j pu  |  |If1| = {abs(If1)/Ibase:.6f} pu ∠ {math.degrees(np.angle(If1)):.2f}°")
print(f"If2: {(If2/Ibase).real:+.6f} {(If2/Ibase).imag:+.6f}j pu  |  |If2| = {abs(If2)/Ibase:.6f} pu ∠ {math.degrees(np.angle(If2)):.2f}°")

# =====================================================
# TENSÃO DE THÉVENIN (pré-falta fase A na relay_position)
# =====================================================
mag_vth    = tensoes_prefalta_reais[0][0]
ang_vth    = tensoes_prefalta_reais[0][1]
Vth        = complex(mag_vth * math.cos(math.radians(ang_vth)),
                     mag_vth * math.sin(math.radians(ang_vth)))
Vth_pu     = Vth / Vbase

# =====================================================
# TENSÕES DE SEQUÊNCIA NO RELAY
# =====================================================
Vs1 = Vth  - If1 * Zth1
Vs2 =      - If2 * Zth2
Vs0 =      - If0 * Zth0

Vs1_pu = Vs1 / Vbase
Vs2_pu = Vs2 / Vbase
Vs0_pu = Vs0 / Vbase

print("\n================ TENSÕES DE SEQUÊNCIA NO RELAY (modelo) ================")
print(f"Vs1: {Vs1_pu.real:+.6f} {Vs1_pu.imag:+.6f}j pu  |  |Vs1| = {abs(Vs1_pu):.6f} pu ∠ {math.degrees(np.angle(Vs1_pu)):.2f}°")
print(f"Vs2: {Vs2_pu.real:+.6f} {Vs2_pu.imag:+.6f}j pu  |  |Vs2| = {abs(Vs2_pu):.6f} pu ∠ {math.degrees(np.angle(Vs2_pu)):.2f}°")
print(f"Vs0: {Vs0_pu.real:+.6f} {Vs0_pu.imag:+.6f}j pu  |  |Vs0| = {abs(Vs0_pu):.6f} pu ∠ {math.degrees(np.angle(Vs0_pu)):.2f}°")

# =====================================================
# V_monitor = Vs1 + Vs2 + Vs0
# =====================================================
V_monitor    = Vs1 + Vs2 + Vs0
V_monitor_pu = V_monitor / Vbase

print("\n================ V_MONITOR (modelo de sequência) ================")
print(f"V_monitor: {V_monitor_pu.real:+.6f} {V_monitor_pu.imag:+.6f}j pu")
print(f"V_monitor: {abs(V_monitor_pu):.6f} pu ∠ {math.degrees(np.angle(V_monitor_pu)):.2f}°")

# =====================================================
# COMPARAÇÃO COM TENSÃO REAL DO OPENDSS (fase A relay)
# =====================================================
mag_real   = tensoes_falta_reais[0][0]
ang_real   = tensoes_falta_reais[0][1]
V_relay    = complex(mag_real * math.cos(math.radians(ang_real)),
                     mag_real * math.sin(math.radians(ang_real)))
V_relay_pu = V_relay / Vbase

erro_mag = abs(abs(V_monitor_pu) - abs(V_relay_pu))
erro_ang = abs(math.degrees(np.angle(V_monitor_pu)) - ang_real)

print("\n================ COMPARAÇÃO V_MONITOR vs V_RELAY (OpenDSS) ================")
print(f"V_relay  (OpenDSS): {V_relay_pu.real:+.6f} {V_relay_pu.imag:+.6f}j pu  |  {abs(V_relay_pu):.6f} pu ∠ {ang_real:.2f}°")
print(f"V_monitor (modelo): {V_monitor_pu.real:+.6f} {V_monitor_pu.imag:+.6f}j pu  |  {abs(V_monitor_pu):.6f} pu ∠ {math.degrees(np.angle(V_monitor_pu)):.2f}°")
print(f"\nErro magnitude: {erro_mag:.6f} pu  ({erro_mag*100:.4f}%)")
print(f"Erro ângulo:    {erro_ang:.4f}°")

# =====================================================
# RESTAURA CIRCUITO ORIGINAL
# =====================================================
dss.text(r"compile C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\34Bus\34busModTotal953mi.dss")
dss.solution.solve()