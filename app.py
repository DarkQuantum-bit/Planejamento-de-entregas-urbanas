from datetime import datetime
from time import perf_counter

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from models.data_generator import DataGenerator
from models.optimizer import VRPTWOptimizer
from utils.visualization import RouteVisualizer


st.set_page_config(page_title="Planejamento de entregas", layout="wide")
st.title("Planejamento de entregas urbanas")
st.caption("Estudo de roteamento urbano com frota heterogênea e janelas de entrega")

with st.sidebar:
    st.header("Cenário")
    deliveries = st.slider("Entregas", 10, 100, 30, step=5)
    cars = st.slider("Carros", 0, 10, 3)
    motorcycles = st.slider("Motos", 0, 15, 5)
    penalty = st.slider("Penalidade por minuto de atraso (R$)", 0.5, 10.0, 2.0, 0.5)
    tolerance = st.slider("Tolerância de atraso (min)", 0, 240, 120, 30)
    seed = st.number_input("Semente do cenário", min_value=0, max_value=1_000_000, value=42)
    run = st.button("Calcular rotas", type="primary", use_container_width=True)
    st.caption("Os dados utilizados são sintéticos.")
    st.caption("As distâncias são representadas pelo raio.")
    
if "history" not in st.session_state:
    st.session_state.history = []

if run:
    if cars + motorcycles == 0:
        st.error("Selecione pelo menos um veículo.")
    else:
        generator = DataGenerator(seed=int(seed))
        points = generator.generate_delivery_points(deliveries)
        fleet = generator.generate_fleet(cars, motorcycles)
        distances = generator.calculate_distance_matrix(points, generator.city_center)
        # The optimizer derives travel times from the speed of each vehicle.
        approximate_times = distances * 60 / 40
        optimizer = VRPTWOptimizer(distances, approximate_times, fleet, points)
        optimizer.time_penalty_per_minute = penalty
        optimizer.max_time_violation = tolerance
        with st.spinner("Calculando rotas..."):
            started = perf_counter()
            try:
                solution = optimizer.solve()
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))
                st.stop()
            elapsed = perf_counter() - started

        st.session_state.current = dict(
            points=points, fleet=fleet, distances=distances, solution=solution,
            solve_time=elapsed, depot=generator.city_center
        )
        st.session_state.history.append(dict(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            deliveries=deliveries, cars=cars, motorcycles=motorcycles,
            served=sum(map(len, solution.routes)), rejected=len(solution.unassigned_points),
            cost=solution.total_cost, distance_km=solution.total_distance,
            solve_seconds=round(elapsed, 2)
        ))

if "current" not in st.session_state:
    st.info("Configure o cenário na barra lateral e clique em **Calcular rotas**.")
    st.stop()

data = st.session_state.current
solution = data["solution"]
served = sum(map(len, solution.routes))
col1, col2, col3, col4 = st.columns(4)
col1.metric("Custo total estimado", f"R$ {solution.total_cost:,.2f}")
col2.metric("Entregas atendidas", served)
col3.metric("Entregas não atendidas", len(solution.unassigned_points))
col4.metric("Distância total", f"{solution.total_distance:,.1f} km")

if solution.unassigned_points:
    st.warning(f"{len(solution.unassigned_points)} entrega(s) não foram alocadas. O custo total inclui a penalidade de rejeição.")

map_tab, details_tab, history_tab = st.tabs(["Rotas", "Indicadores", "Histórico"])
with map_tab:
    st.caption("Trajetos esquemáticos entre coordenadas geográficas; não representam caminhos reais sobre ruas.")
    viz = RouteVisualizer(*data["depot"])
    map_obj = viz.create_map(solution.routes, data["points"],
                             [data["fleet"][i] for i in solution.vehicle_assignments], solution.metrics)
    st_folium(map_obj, height=520, use_container_width=True, returned_objects=[])
    if solution.routes:
        route_table = []
        for route, vehicle_index in zip(solution.routes, solution.vehicle_assignments):
            vehicle = data["fleet"][vehicle_index]
            route_table.append({"Veículo": f"{vehicle.type} {vehicle.id + 1}",
                                "Entregas": len(route), "Sequência": " → ".join(map(str, route))})
        st.dataframe(pd.DataFrame(route_table), use_container_width=True, hide_index=True)
    else:
        st.info("Não há rotas viáveis nesse cenário.")

with details_tab:
    st.subheader("Composição de custo")
    breakdown = pd.DataFrame([
        {"Componente": "Veículos e deslocamentos", "Custo (R$)": solution.metrics["operating_cost"]},
        {"Componente": "Atrasos", "Custo (R$)": solution.metrics["late_penalties"]},
        {"Componente": "Entregas rejeitadas", "Custo (R$)": solution.metrics["rejection_penalties"]},
    ])
    st.dataframe(breakdown, use_container_width=True, hide_index=True)
    st.metric("Frota utilizada", f'{solution.metrics["fleet_utilization"]:.0f}%')
    st.metric("Tempo de processamento", f'{data["solve_time"]:.2f} s')
    st.caption("O modelo utiliza busca heurística. O resultado não é certificado como ótimo global.")

with history_tab:
    history = pd.DataFrame(st.session_state.history)
    st.dataframe(history, use_container_width=True, hide_index=True)
    if len(history) > 1:
        st.line_chart(history.set_index("timestamp")[["cost"]])
    st.caption("O histórico permanece apenas nesta sessão e os cenários podem ter tamanhos diferentes.")
