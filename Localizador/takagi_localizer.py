import cmath

# =====================================================
# IMPLEMENTAÇÃO DO LOCALIZADOR DE TAKAGI
# =====================================================
def calcular_localizacao_takagi(Vs, Is, Is_pre, ZL):
    """
    Calcula a distância da falta em p.u. (por unidade) usando o método de Takagi.
    
    Parâmetros:
    Vs     : Tensão complexa de fase no terminal local durante a falta (V)
    Is     : Corrente complexa de fase no terminal local durante a falta (A)
    Is_pre : Corrente complexa de fase no terminal local em pré-falta (A)
    ZL     : Impedância complexa total da linha de transmissão (Ohm)
    
    Retorno:
    d      : Distância estimada da falta em p.u. (valor entre 0 e 1)
    """
    
    # 1. Cálculo da corrente de sobreposição (Delta I)
    # Esta corrente é usada como referência de fase para eliminar o erro de Rf
    delta_Is = Is - Is_pre
    
    # 2. Conjugado complexo da corrente de sobreposição
    delta_Is_conj = delta_Is.conjugate()
    
    # 3. Numerador da fórmula: Im(Vs * delta_Is*)
    numerador = (Vs * delta_Is_conj).imag
    
    # 4. Denominador da fórmula: Im(ZL * Is * delta_Is*)
    denominador = (ZL * Is * delta_Is_conj).imag
    
    # 5. Cálculo da distância d
    try:
        d = numerador / denominador
    except ZeroDivisionError:
        d = None
        print("Erro: Denominador nulo. Verifique os parâmetros de entrada.")
        
    return d

# Exemplo de uso (Pode ser removido ou comentado):
if __name__ == "__main__":
    # Exemplo de valores complexos (Forma retangular: real + imagj)
    vs_falta = complex(120000, -5000)  # Tensão durante a falta
    is_falta = complex(1200, -800)     # Corrente durante a falta
    is_pre   = complex(400, -100)      # Corrente de carga antes da falta
    zl_total = complex(5, 40)          # Impedância total da linha (R + jX)

    distancia = calcular_localizacao_takagi(vs_falta, is_falta, is_pre, zl_total)
    
    if distancia is not None:
        print(f"Distância estimada da falta: {distancia:.4f} p.u.")