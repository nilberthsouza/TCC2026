# Fichamentos


## Referencia 1

**Cite this:** R. Marguet and B. Raison, "Fault distance localization method for heterogeneous distribution networks," 2014 IEEE PES General Meeting | Conference & Exposition, National Harbor, MD, USA, 2014, pp. 1-5, doi: 10.1109/PESGM.2014.6939025. 

**Objetivo:** Descrever um método de localização de faltas para redes de distribuição heterogêneas que pode ser implementado aproveitando os desenvolvimentos atuais de redes inteligentes (*smart grids*). O foco é superar a complexidade de estruturas radiais e a forte heterogeneidade dos condutores.

**Metodologia:**

* 
**Adaptação do Algoritmo de Takagi**: O método utiliza o algoritmo de Takagi, originalmente desenvolvido para redes de transmissão, adaptando-o para o contexto da distribuição.


* 
**Teoria de Quadripolos**: A rede é modelada como uma sequência de seções homogêneas. Cada elemento da rede (linhas e cargas) é considerado como um quadripolo representado por matrizes de transferência do tipo $B$.


* 
**Propagação de Medições**: Tensão e corrente medidas na subestação (cabeça do alimentador) são propagadas através do cálculo de matrizes equivalentes até a entrada de cada seção homogênea.


* 
**Cálculo Iterativo**: A localização é feita seção por seção. Se a distância da falta calculada for superior ao comprimento da seção atual, o algoritmo passa para a próxima seção a jusante.


* 
**Simulação**: Validação através de simulações no software EMTP/ATPDraw usando dados reais de um alimentador rural francês de 20 kV.



**Principais Resultados:**

* 
**Precisão de Distância**: Nos casos onde a seção foi corretamente identificada, o erro máximo de distância foi de apenas 0,29% (8 metros). O erro máximo absoluto em todas as 31 simulações foi de 163 metros (1,6% de erro relativo).


* 
**Eficiência da Propagação**: Em condições normais, o erro de propagação de tensão foi inferior a 0,013%. O erro de corrente foi mantido abaixo de 1% em extensões de até 17 km.


* 
**Múltiplas Localizações**: Devido à natureza radial da rede, o algoritmo frequentemente propõe mais de uma seção como possivelmente faltosa (em um caso, chegou a propor 12 seções).


* 
**Identificação de Seção**: O algoritmo sempre incluiu a seção correta (ou as seções a jusante conectadas ao ponto de falta) entre os resultados propostos.



**Conclusões:**

* O método prova ser eficaz para lidar com a heterogeneidade das redes de distribuição sem a necessidade de aproximar impedâncias médias, o que geraria resultados imprecisos.


* A facilidade de execução com poucos dados em tempo real torna o método um passo interessante para a localização de faltas em redes modernas.


* 
**Limitação**: O algoritmo precisa ser associado a outros métodos (como indicadores de falta ou sensores ao longo do alimentador) para discriminar qual das seções propostas é a verdadeira localização.



**Críticas e Reflexões:**

* 
**Escopo de Faltas**: O estudo focou em faltas fase-terra metálicas (resistência de falta de $0,1\text{ m}\Omega$), sendo necessário evoluir para contemplar faltas com arco e diferentes tipos de aterramento de neutro.


* 
**Condições Reais**: Os autores admitem que a performance pode diminuir em aplicações práticas fora do ambiente de simulação e pretendem confrontar o algoritmo com medições reais no futuro.



**Referências e Relações:**

* O trabalho baseia-se em métodos clássicos de impedância de loop (reatância de sequência positiva e Takagi).


* Utiliza a representação de componentes de rede como quadripolos independentes baseada em componentes simétricas.

## Referencia 2


**Referência:** L. Wang, Z. Deng and M. Ma, "Fault Location Method for Distribution Network Based on Improved Apparent Impedance," *2019 IEEE Sustainable Power and Energy Conference (iSPEC)*, Beijing, China, 2019, pp. 2556-2560. doi: 10.1109/iSPEC48194.2019.8974882.

**Objetivo:** Propor um método aprimorado de localização de faltas baseado em impedância aparente e busca binária para redes de distribuição, visando superar as limitações de métodos tradicionais que exigem parâmetros de linha uniformes.

**Metodologia:**

* 
**Algoritmo de Impedância Aparente:** Utiliza medições de tensão e corrente de terminal único na subestação para calcular a reatância de falta.


* 
**Busca Binária (Dicotomia):** Em vez de calcular a distância diretamente, o método utiliza uma busca binária ao longo da topologia da rede para identificar o ponto onde a diferença entre a reatância calculada e a reatância real da linha é mínima.


* 
**Tratamento de Heterogeneidade:** O método considera parâmetros distintos para diferentes tipos de condutores (cabos e linhas aéreas), eliminando a necessidade de assumir uma impedância média uniforme.


* 
**Simulação:** Validação realizada através da integração entre os softwares OpenDSS (para modelagem da rede e simulação de faltas) e MATLAB (para execução do algoritmo de localização).



**Principais Resultados:**

* 
**Precisão Elevada:** Em testes simulados em uma rede real, o erro relativo de localização foi geralmente inferior a 5%.


* 
**Sensibilidade à Distância:** Observou-se que o erro tende a aumentar gradualmente à medida que a distância entre o ponto de falta e o dispositivo de monitoramento aumenta.


* 
**Impacto de Fatores Externos:** A resistência de falta e a carga da linha possuem um impacto pequeno na precisão, mantendo os erros dentro de faixas aceitáveis para a operação da rede.



**Conclusões:**

* O método proposto é adequado para redes de distribuição com baixo nível de automação, pois requer apenas equipamentos de monitoramento na subestação.


* A abordagem de comparação de reatâncias via busca binária resolve eficazmente o problema da heterogeneidade de condutores em estruturas complexas.


* A confiabilidade do método foi verificada por meio de extensivos testes de simulação em topologias de redes de distribuição reais.



**Críticas e Reflexões:**

* O estudo foca primariamente em faltas monofásicas à terra, que representam a maioria das ocorrências, mas a complexidade de redes com múltiplas derivações ainda pode gerar desafios na identificação da ramificação correta.


* A dependência de parâmetros precisos da linha (topologia e tipos de condutores) é um pré-requisito crítico para o sucesso do algoritmo.



**Referências e Relações:**

* Relaciona-se com estudos clássicos de localização baseada em impedância (Girgis et al.) e métodos de busca por dicotomia aplicados a sistemas elétricos (Ou Liquan et al.).

## Referencia 3


**Referência:** S. Kulkarni, N. Karnik, S. Das and S. Santoso, "Fault location using impedance-based algorithms on non-homogeneous feeders," *2011 IEEE Power and Energy Society General Meeting*, Detroit, MI, USA, 2011, pp. 1-6. doi: 10.1109/PES.2011.6039257. 

**Objetivo:** Demonstrar que algoritmos de localização de faltas baseados em impedância, originalmente derivados para linhas homogêneas, podem ser aplicados de forma eficaz em alimentadores de distribuição não homogêneos ao utilizar os parâmetros do tipo de condutor mais comum no circuito. 

**Metodologia:**

* 
**Seleção de Algoritmos:** O estudo foca no método da reatância de sequência positiva e no método de Takagi. 


* 
**Abordagem de Parâmetro Único:** Em vez de modelar cada seção individualmente, utiliza-se a impedância por unidade de comprimento do condutor predominante em todo o cálculo. 


* 
**Simulação de Teste:** O método foi testado em um alimentador de teste da IEEE modificado, comparando um cenário de referência (não homogêneo) com um caso ideal (homogêneo). 


* 
**Validação Real:** A abordagem foi demonstrada através da análise de dez casos reais de faltas em alimentadores de concessionárias de energia. 



**Principais Resultados:**

* 
**Desempenho em Simulação:** No caso do alimentador não homogêneo simulado, o erro máximo absoluto foi de 8% para o método da reatância de sequência positiva e 9,53% para o método de Takagi. 


* 
**Desempenho em Casos Reais:** A média do erro absoluto para os dez casos reais analisados foi de 10,23% (0,16 milhas) para o método de reatância e 9,34% (0,15 milhas) para o de Takagi. 


* 
**Sensibilidade ao Condutor:** O estudo verificou que a escolha do condutor "dominante" para os cálculos é uma simplificação viável que mantém a precisão dentro de limites aceitáveis para a operação. 



**Conclusões:**

* Algoritmos baseados em impedância são robustos o suficiente para fornecer estimativas úteis mesmo quando a premissa de homogeneidade do condutor é violada. 


* A precisão obtida (erro mediano em torno de 0,15 milhas) é considerada satisfatória para auxiliar equipes de campo na localização física da falta em alimentadores de distribuição. 



**Críticas e Reflexões:**

* O artigo foca na viabilidade prática da simplificação de parâmetros, o que é valioso para concessionárias com bases de dados de ativos incompletas. 


* Entretanto, erros de cerca de 10% podem ser significativos em alimentadores muito longos, sugerindo que o método é mais uma ferramenta de triagem do que de precisão absoluta. 



**Referências e Relações:**

* O trabalho expande a aplicação de algoritmos clássicos como o de Takagi (1982). 


* Complementa outros estudos sobre o efeito da corrente de carga e da resistência de falta na estimativa de localização.

## Referencia 4


**Referência:** X. Shao, W. Cong, Y. Liang, X. Yu and K. Li, "Fault Positioning Method for Distribution Systems Built Upon Positive Sequence Fault Components," *2025 10th Asia Conference on Power and Electrical Engineering (ACPEE)*, Beijing, China, 2025, pp. 1-5. doi: 10.1109/ACPEE64358.2025.11041556. 

**Objetivo:** Propor uma técnica inovadora de localização de faltas entre fases em redes de distribuição de média e baixa tensão, integrando o componente de falta de sequência positiva ao método de impedância de duas extremidades. 

**Metodologia:**

* 
**Modelo de Linha:** Utiliza o modelo equivalente de linha do tipo $\pi$ para simplificar os cálculos em redes de distribuição com linhas relativamente curtas. 


* 
**Componentes de Sequência Positiva:** Isola estes componentes das tensões e correntes das barras em ambos os lados da rede (fonte dupla) para anular efeitos de carga, resistência de transição e indutância mútua. 


* 
**Método da Dicotomia (Busca Binária):** Aplica uma busca iterativa partindo do ponto médio da linha; o algoritmo calcula as tensões de sequência positiva no ponto hipotético a partir de ambos os terminais e refina a busca comparando a diferença de fase e amplitude entre elas. 


* 
**Processamento de Sinais:** Emprega o algoritmo de Filtro de Kalman para remover ruídos e harmônicos, seguido da Transformada de Fourier para conversão em fasores. 


* 
**Simulação:** Validado via software PSCAD/EMTDC em um modelo de rede de 10 kV e 10 km de extensão. 



**Principais Resultados:**

* 
**Alta Precisão:** O erro de localização da falta não ultrapassou **2%** do comprimento total da linha em diversos cenários simulados. 


* 
**Desempenho por Tipo de Falta:** Demonstrou eficácia em faltas bifásicas (B-C), bifásicas à terra e trifásicas, com erros variando entre 0% e 1,375% nas tabelas de teste. 


* 
**Robustez:** O método provou ser independente do tipo de falta e imune a variações na resistência de transição e corrente de carga. 



**Conclusões:**

* A integração de componentes de sequência positiva com o método da dicotomia resolve desafios de precisão em redes de distribuição complexas. 


* O método possui alto valor para aplicação em engenharia por ser de fácil implementação e exigir menos recursos computacionais que algoritmos inteligentes baseados em treinamento de dados. 



**Críticas e Reflexões:**

* Embora o método seja robusto para faltas entre fases, o artigo foca em sistemas com fontes em ambas as extremidades (*dual sources*), o que pode limitar a aplicação em ramais radiais puros sem geração distribuída ou interconexão. 


* A precisão depende da acurácia dos parâmetros da linha e da sincronização das medições em ambas as extremidades. 



**Referências e Relações:**

* Relaciona-se com o método de impedância clássico , mas busca superar as limitações deste em relação à resistência de transição usando componentes de sequência. 


* Contrapõe-se a métodos de onda viajante (*traveling wave*) por exigir hardware menos sofisticado e caro.

## Referencia 5

**Referência:** R. F. Buzo, H. M. Barradas and F. B. Leão, "A New Method for Fault Location in Distribution Networks Based on Voltage Sag Measurements," in *IEEE Transactions on Power Delivery*, vol. 36, no. 2, pp. 651-662, April 2021. doi: 10.1109/TPWRD.2020.2987892.

**Objetivo:** Apresentar um método inovador de localização de faltas em redes de distribuição baseado na análise de afundamentos de tensão (*voltage sags*), utilizando medições de tensão pré-falta e durante a falta em apenas alguns nós da rede.

**Metodologia:**

* **Análise de Circuitos Clássica:** O método fundamenta-se em conceitos fundamentais de análise de circuitos e manipulação da matriz de impedância nodal ($Z_{bus}$).
* **Particionamento do Sistema:** Uma nova técnica de manipulação de matrizes é proposta para dividir o sistema de distribuição em múltiplos subsistemas menores.
* **Medições Sincronizadas e Não-Sincronizadas:** O algoritmo requer dois medidores de tensão sincronizados (PMUs) e alguns medidores não-sincronizados distribuídos em nós estratégicos.
* **Equações Determinadas:** A localização é realizada resolvendo sistemas de equações determinados para cada subsistema separadamente, reduzindo a complexidade computacional.
* **Validação:** O método foi testado no sistema IEEE de 33 barras (12,66 kV), considerando cenários com e sem a presença de Geração Distribuída (GD).

**Principais Resultados:**

* **Alta Precisão:** O método apresentou erros extremamente baixos em diversos tipos de faltas (monofásicas, bifásicas e trifásicas).
* **Robustez à GD:** A presença de geradores distribuídos não comprometeu a precisão, pois o impacto da GD é incorporado através das variações de tensão medidas.
* **Resistência de Falta:** Demonstrou ser eficaz mesmo em faltas com diferentes níveis de resistência de transição.
* **Erros de Medição:** O algoritmo manteve um desempenho satisfatório mesmo quando submetido a erros típicos de medição e variações de carga.

**Conclusões:**

* A divisão da rede em subsistemas torna o processo de localização tecnicamente mais acessível e computacionalmente eficiente.
* O método resolve o problema da necessidade de medições em todas as barras, tornando-o viável para redes reais onde o monitoramento total é economicamente inviável.
* A abordagem baseada em afundamentos de tensão é uma alternativa robusta aos métodos baseados em impedância aparente de terminal único.

**Críticas e Reflexões:**

* O artigo propõe uma solução elegante para a multiplicidade de resultados (pontos de falta com a mesma impedância aparente), facilitando a identificação da ramificação correta.
* Embora exija poucas medições, o desempenho ideal ainda depende da presença de ao menos dois pontos de medição sincronizados, o que pode ser um desafio em redes de distribuição de baixa tecnologia.

**Referências e Relações:**

* Relaciona-se com estudos de localização de faltas baseados em matrizes de impedância e métodos de estimativa de afundamento de tensão.
* Complementa a literatura que busca integrar o monitoramento de Qualidade de Energia com funções de proteção e diagnóstico de redes inteligentes.