import os
import pathlib
import py_dss_interface
import numpy as np

# Caminho
script_path = os.path.dirname(os.path.abspath(__file__))
#dss_file = pathlib.Path(script_path).joinpath("34Bus", "ieee34Mod1.dss")
#dss_file = pathlib.Path(script_path).joinpath("sistema.dss")

# Inicializa
dss = py_dss_interface.DSS()
dss.text(f"compile [{dss_file}]")

# Fluxo de potência
dss.text("set mode=Snapshot")
dss.text("solve")

# Curto-circuito
dss.text("set mode=FaultStudy")
dss.text("solve")

print("\n=== CORRENTES DE CURTO ===\n")

# Loop nas barras
for bus in dss.circuit.buses_names:
    dss.circuit.set_active_bus(bus)

    isc = dss.bus.isc

    if len(isc) == 0:
        continue

    # Converte para complexo
    isc_complex = np.array(isc[0::2]) + 1j * np.array(isc[1::2])
    isc_mag = np.abs(isc_complex)

    print(f"Barra: {bus}")

    # Trifásico (aproximação)
    if len(isc_mag) >= 3:
        i3f = max(isc_mag[:3])
        print(f"  Icc 3φ ≈ {i3f:.2f} A")

    # Monofásico
    for i, val in enumerate(isc_mag):
        print(f"  Fase {i+1}: Icc 1φ ≈ {val:.2f} A")

    print("-" * 40)