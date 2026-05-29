"""
diagnostico5.py
---------------
Investiga:
  A) Quais barras têm kv_base != 0 após Set VoltageBases=[100]
  B) Se buses_vmag retorna correto para todas as barras
  C) Se vmag_angle funciona via índice em vez de set_active_bus
  D) Se cktelement.voltages_mag_ang funciona para correntes
"""
import py_dss_interface
import numpy as np

DSS_FILE = r"C:\Users\nilbe\Documents\DISCIPLINAS\TCC2026\Localizador\69bus.dss"

dss = py_dss_interface.DSS()
dss.text(f"compile {DSS_FILE}")
dss.text("Set VoltageBases=[100]")
dss.text("CalcVoltageBases")
dss.text("Solve")

names = dss.circuit.buses_names
vmags = dss.circuit.buses_vmag

print("=" * 60)
print("A — kv_base e buses_vmag por barra")
print("=" * 60)
for bus in ["sourcebus", "1", "2", "3", "4", "5", "6", "19", "28"]:
    try:
        idx = [n.lower() for n in names].index(bus.lower())
        dss.circuit.set_active_bus(bus)
        kv = dss.bus.kv_base
        vmag_idx = vmags[idx]
        vmag_ang = dss.bus.vmag_angle
        print(f"  Barra {bus:>10}: kv_base={kv:.4f} kV  "
              f"buses_vmag={vmag_idx:.1f} V  "
              f"vmag_angle[0]={vmag_ang[0]:.1f}")
    except Exception as e:
        print(f"  Barra {bus}: ERRO {e}")

print()
print("=" * 60)
print("B — voltages via cktelement (linha l1_2 e l2_3)")
print("=" * 60)
for line in ["Line.l1_2", "Line.l2_3", "Line.l4_5"]:
    dss.circuit.set_active_element(line)
    try:
        v = dss.cktelement.voltages_mag_ang
        print(f"  {line}: voltages_mag_ang[0:4] = {[round(x,1) for x in v[:4]]}")
    except Exception as e:
        print(f"  {line}: voltages_mag_ang ERRO {e}")
    try:
        c = dss.cktelement.currents_mag_ang
        print(f"  {line}: currents_mag_ang[0:4] = {[round(x,4) for x in c[:4]]}")
    except Exception as e:
        print(f"  {line}: currents_mag_ang ERRO {e}")

print()
print("=" * 60)
print("C — nodes_vmag_by_phase (alternativa a vmag_angle)")
print("=" * 60)
try:
    # retorna dict-like ou lista por fase
    v_phase = dss.circuit.nodes_vmag_by_phase
    print(f"  type: {type(v_phase)}")
    print(f"  valor: {v_phase}")
except Exception as e:
    print(f"  ERRO: {e}")

print()
print("=" * 60)
print("D — y_node_varray leitura completa (primeiros 10 nós)")
print("=" * 60)
nodes = dss.circuit.y_node_order
varray = dss.circuit.y_node_varray
print(f"  Total nós: {len(nodes)}, y_node_varray len: {len(varray)}")
for k in range(min(10, len(nodes))):
    re = varray[2*k]
    im = varray[2*k+1]
    mag = abs(complex(re, im))
    print(f"  nó {nodes[k]:>8}: |V| = {mag:.1f} V")