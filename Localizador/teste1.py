import cmath
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
# TENSÃO LL NA BARRA DO RELAY (fasorial complexa)
# =====================================================
# tensoes_prefalta_reais contém [(mag, ang), ...] para cada fase
# Fase A = índice 0, Fase B = índice 1, Fase C = índice 2

# Tensão fase-neutro fasorial de cada fase
VA = cmath.rect(tensoes_prefalta_reais[0][0], math.radians(tensoes_prefalta_reais[0][1]))
VB = cmath.rect(tensoes_prefalta_reais[1][0], math.radians(tensoes_prefalta_reais[1][1]))
VC = cmath.rect(tensoes_prefalta_reais[2][0], math.radians(tensoes_prefalta_reais[2][1]))

# Tensão linha-linha fasorial: VAB = VA - VB
VAB = VA - VB

kV_LL = VAB / 1000  # em kV, fasorial

print("\n================ TENSÃO LL NA BARRA (kV) ================")
print(f"VAB: {abs(kV_LL):.4f} kV ∠ {math.degrees(cmath.phase(kV_LL)):.2f}°")

# =====================================================
# CORRENTES DE CURTO FASORIAIS (fase A — terminal 2 de Line.L5)
# =====================================================
# correntes_cc3f_reais[0] = fase A do curto 3F
# correntes_cc1f_reais[0] = fase A do curto 1F-T

I3phi_sc = cmath.rect(correntes_cc3f_reais[0][0], math.radians(correntes_cc3f_reais[0][1]))
I1phi_sc = cmath.rect(correntes_cc1f_reais[0][0], math.radians(correntes_cc1f_reais[0][1]))

print("\n================ CORRENTES DE CURTO FASORIAIS ================")
print(f"I3phi_sc (Fase A, 3F): {abs(I3phi_sc):.4f} A ∠ {math.degrees(cmath.phase(I3phi_sc)):.2f}°")
print(f"I1phi_sc (Fase A, 1F): {abs(I1phi_sc):.4f} A ∠ {math.degrees(cmath.phase(I1phi_sc)):.2f}°")

# =====================================================
# CÁLCULO DAS IMPEDÂNCIAS DE SEQUÊNCIA
# =====================================================
# Z1_eq = kV_LL / (sqrt(3) * I3phi_sc)
# Z0_eq = (sqrt(3) * kV_LL) / I1phi_sc - 2 * Z1_eq

Z1_eq = kV_LL / (3**0.5 * I3phi_sc)
Z0_eq = (3**0.5 * kV_LL) / I1phi_sc - 2 * Z1_eq

# Converter para ohms (kV → V já cancela com A, mas kV/A = kΩ → × 1000)
Z1_eq_ohm = Z1_eq * 1000
Z0_eq_ohm = Z0_eq * 1000

# Em pu
Z1_eq_pu = Z1_eq_ohm / Zbase
Z0_eq_pu = Z0_eq_ohm / Zbase

print("\n================ IMPEDÂNCIAS DE SEQUÊNCIA ================")
print(f"Z1_eq: {abs(Z1_eq_ohm):.6f} Ω ∠ {math.degrees(cmath.phase(Z1_eq_ohm)):.2f}°")
print(f"       R1 = {Z1_eq_ohm.real:.6f} Ω  |  X1 = {Z1_eq_ohm.imag:.6f} Ω")
print(f"       Z1_eq (pu): {abs(Z1_eq_pu):.6f} ∠ {math.degrees(cmath.phase(Z1_eq_pu)):.2f}°")

print(f"\nZ0_eq: {abs(Z0_eq_ohm):.6f} Ω ∠ {math.degrees(cmath.phase(Z0_eq_ohm)):.2f}°")
print(f"       R0 = {Z0_eq_ohm.real:.6f} Ω  |  X0 = {Z0_eq_ohm.imag:.6f} Ω")
print(f"       Z0_eq (pu): {abs(Z0_eq_pu):.6f} ∠ {math.degrees(cmath.phase(Z0_eq_pu)):.2f}°")