import folium
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict
import pandas as pd
import numpy as np
from streamlit_folium import folium_static

class RouteVisualizer:
    """Classe para visualização das rotas"""
    
    def __init__(self, depot_lat: float, depot_lon: float):
        self.depot_lat = depot_lat
        self.depot_lon = depot_lon
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                      '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
    
    def create_map(self, routes: List[List[int]], points: List, 
                  vehicles: List, metrics: Dict = None) -> folium.Map:
        """Cria mapa interativo com as rotas"""

        # Cria mapa centrado no depósito
        m = folium.Map(
            location=[self.depot_lat, self.depot_lon],
            zoom_start=13,
            tiles='CartoDB positron'
        )

        # Adiciona marcador do depósito
        folium.Marker(
            [self.depot_lat, self.depot_lon],
            popup='Depósito',
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)

        # Adiciona pontos de entrega e rotas
        for route_idx, (route, vehicle) in enumerate(zip(routes, vehicles)):
            color = self.colors[route_idx % len(self.colors)]
            
            # Verifica se vehicle é um objeto Vehicle ou um inteiro
            if hasattr(vehicle, 'id'):
                vehicle_id = vehicle.id
                vehicle_type = getattr(vehicle, 'type', 'veículo')
                vehicle_capacity = getattr(vehicle, 'capacity', 0)
            else:
                # Se for um inteiro, usa diretamente
                vehicle_id = int(vehicle)
                vehicle_type = f"Veículo {vehicle_id + 1}"
                vehicle_capacity = 0

            # Adiciona pontos da rota
            route_coords = [(self.depot_lat, self.depot_lon)]

            for point_id in route:
                point = points[point_id - 1]

                # Determina cor do marcador baseado na prioridade
                marker_color = 'green' if point.priority == 1 else \
                              'orange' if point.priority == 2 else 'gray'

                # Adiciona marcador do ponto
                folium.CircleMarker(
                    [point.lat, point.lon],
                    radius=5,
                    popup=f"Ponto {point.id}<br>Demanda: {point.demand}<br>"
                          f"Janela: {point.time_window_start//60}h{point.time_window_start%60:02d}-"
                          f"{point.time_window_end//60}h{point.time_window_end%60:02d}",
                    color=color,
                    fill=True,
                    fill_color=marker_color
                ).add_to(m)

                route_coords.append((point.lat, point.lon))

            # Fecha a rota
            route_coords.append((self.depot_lat, self.depot_lon))

            # Adiciona linha da rota
            folium.PolyLine(
                route_coords,
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"Rota {route_idx + 1} - {vehicle_type} (ID: {vehicle_id + 1})"
            ).add_to(m)
        
        # Adiciona legenda
        legend_html = """
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; 
                    background-color: white; padding: 10px; border-radius: 5px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
            <b>Legenda</b><br>
            <span style="color: green;">●</span> Alta prioridade<br>
            <span style="color: orange;">●</span> Média prioridade<br>
            <span style="color: gray;">●</span> Baixa prioridade<br>
            <span style="color: red;">●</span> Depósito
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
    
    def create_metrics_chart(self, routes: List[List[int]], 
                           points: List, vehicles: List) -> go.Figure:
        """Cria gráfico de métricas"""

        # Calcula métricas por rota
        route_data = []
        for i, (route, vehicle) in enumerate(zip(routes, vehicles)):
            # Verifica se vehicle é um objeto Vehicle ou um inteiro
            if hasattr(vehicle, 'id'):
                vehicle_id = vehicle.id
                vehicle_type = getattr(vehicle, 'type', 'veículo')
                vehicle_capacity = getattr(vehicle, 'capacity', 0)
            else:
                vehicle_id = int(vehicle)
                vehicle_type = f"Veículo {vehicle_id + 1}"
                vehicle_capacity = 0
            
            total_demand = sum(points[p-1].demand for p in route)
            total_points = len(route)

            route_data.append({
                'Rota': f'Rota {i+1}',
                'Veículo': f"Veículo {vehicle_id + 1} ({vehicle_type})",
                'Pontos': total_points,
                'Demanda': total_demand,
                'Capacidade': vehicle_capacity
            })
        
        df = pd.DataFrame(route_data, columns=["Rota", "Veículo", "Pontos", "Demanda", "Capacidade"])
        
        # Cria gráfico de barras empilhadas
        fig = go.Figure(data=[
            go.Bar(name='Demanda', x=df['Rota'], y=df['Demanda']),
            go.Bar(name='Capacidade', x=df['Rota'], y=df['Capacidade'],
                  marker_pattern_shape="/")
        ])
        
        fig.update_layout(
            title='Utilização da Frota por Rota',
            xaxis_title='Rota',
            yaxis_title='Quantidade de Pacotes',
            barmode='group',
            template='plotly_white'
        )
        
        return fig