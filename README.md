# Projeto de pesquisa operacional: planejamento de entregas urbanas 

Aplicação de roteamento de entregas com frota mista (carros e motos), restrições de capacidade e janelas de atendimento. O objetivo é comparar a viabilidade e o custo operacional de diferentes cenários de distribuição.

O projeto usa dados **sintéticos** de entregas posicionadas em torno de São Paulo. Não representa uma malha viária real nem utiliza informações de uma transportadora.

## O problema

Cada entrega possui uma demanda, intervalo de atendimento e duração de serviço. Os veículos têm capacidades, velocidades e custos diferentes. O planejador procura rotas que respeitem a capacidade, contabilizando viagens, uso de veículos e eventuais atrasos.

A função de custo é:

\[
 C = \sum_{v\in V_{uso}} f_v + \sum_{v\in V}\sum_{(i,j)\in R_v} c_v d_{ij} + \lambda\sum_{i\in A} \max(0,t_i-b_i) + P|U|.
\]

- `f_v`: custo fixo de acionar o veículo;
- `c_v`: custo por quilômetro do veículo;
- `d_ij`: distância entre locais;
- `b_i`: fim da janela de entrega;
- `t_i`: horário de atendimento estimado;
- `U`: entregas não atendidas;
- `P`: penalidade por entrega rejeitada.

O modelo usa OR-Tools Routing Solver, com busca inicial por arco de menor custo e refinamento por *Guided Local Search*. É uma abordagem heurística: não há garantia de ótimo global.

## Como usar

Defina tamanho da frota, número de entregas e tolerância a atraso na barra lateral, depois clique em **Otimizar rotas**. O mapa mostra cada roteiro; as abas seguintes apresentam indicadores e histórico da sessão.

## Organização

`models/data_generator.py` gera instâncias; `models/optimizer.py` formula e resolve o VRPTW; `utils/metrics.py` calcula indicadores; `utils/visualization.py` gera os mapas e gráficos; `app.py` integra a interface.

## Tecnologias

Python · Google OR-Tools · Streamlit · Folium · Plotly · NumPy · Pandas
