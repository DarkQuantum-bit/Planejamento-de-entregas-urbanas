import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple
import random

@dataclass
class Vehicle:
    """Representa um veículo da frota"""
    id: int
    type: str  # 'car' ou 'motorcycle'
    capacity: int
    cost_per_km: float
    fixed_cost: float
    speed_kmh: float
    co2_emission: float  # kg CO2 por km

@dataclass
class DeliveryPoint:
    """Representa um ponto de entrega"""
    id: int
    lat: float
    lon: float
    demand: int  # quantidade de pacotes
    time_window_start: int  # minutos desde a meia-noite
    time_window_end: int
    service_time: int  # minutos para entregar
    priority: int  # 1=alta, 2=media, 3=baixa

class DataGenerator:
    """Gera dados sintéticos realistas para o problema de roteamento"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
        
        # Centro da cidade (ex: São Paulo)
        self.city_center = (-23.5505, -46.6333)
        
    def generate_delivery_points(self, n_points: int, area_radius_km: float = 5.0) -> List[DeliveryPoint]:
        """Gera pontos de entrega distribuídos em uma área urbana"""
        points = []
        
        # Distribuição não uniforme (mais denso no centro)
        for i in range(n_points):
            # Usa distribuição normal para criar clusters
            angle = np.random.uniform(0, 2 * np.pi)
            distance = np.random.gamma(shape=2, scale=area_radius_km/3)
            
            # Converte para coordenadas
            lat_offset = (distance * np.cos(angle)) / 111.32  # 1 grau = 111.32 km
            lon_offset = (distance * np.sin(angle)) / (111.32 * np.cos(np.radians(self.city_center[0])))
            
            lat = self.city_center[0] + lat_offset
            lon = self.city_center[1] + lon_offset
            
            # Gera demanda realista (distribuição de Poisson)
            demand = np.random.poisson(lam=3) + 1  # 1-7 pacotes
            
            # Janelas de tempo realistas
            if i % 3 == 0:  # Manhã
                window_start = np.random.randint(480, 600)  # 8:00-10:00
            elif i % 3 == 1:  # Tarde
                window_start = np.random.randint(720, 840)  # 12:00-14:00
            else:  # Fim de tarde
                window_start = np.random.randint(960, 1080)  # 16:00-18:00
            
            window_end = window_start + np.random.randint(120, 240)  # 2-4 horas de janela
            
            # Tempo de serviço baseado na demanda
            service_time = 2 + demand * 1.5  # 3.5 a 12.5 minutos
            
            # Prioridade (mais pacotes = mais prioritário)
            if demand >= 5:
                priority = 1
            elif demand >= 3:
                priority = 2
            else:
                priority = 3
            
            points.append(DeliveryPoint(
                id=i + 1,
                lat=lat,
                lon=lon,
                demand=demand,
                time_window_start=window_start,
                time_window_end=window_end,
                service_time=int(service_time),
                priority=priority
            ))
        
        return points
    
    def generate_fleet(self, n_cars: int = 3, n_motorcycles: int = 5) -> List[Vehicle]:
        """Gera uma frota heterogênea"""
        fleet = []
        
        # Carros (maior capacidade, mais caros)
        for i in range(n_cars):
            fleet.append(Vehicle(
                id=i,
                type='car',
                capacity=20,
                cost_per_km=2.5,
                fixed_cost=50.0,
                speed_kmh=35.0,  # Trânsito urbano
                co2_emission=0.12
            ))
        
        # Motos (menor capacidade, mais baratas e rápidas)
        for i in range(n_motorcycles):
            fleet.append(Vehicle(
                id=n_cars + i,
                type='motorcycle',
                capacity=8,
                cost_per_km=1.2,
                fixed_cost=20.0,
                speed_kmh=45.0,  # Mais ágeis no trânsito
                co2_emission=0.05
            ))
        
        return fleet
    
    def calculate_distance_matrix(self, points: List[DeliveryPoint], depot: Tuple[float, float]) -> np.ndarray:
        """Calcula matriz de distâncias usando fórmula de Haversine"""
        n = len(points) + 1  # +1 para o depósito
        distance_matrix = np.zeros((n, n))
        
        # Coordenadas incluindo depósito
        coords = [(depot[0], depot[1])] + [(p.lat, p.lon) for p in points]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_matrix[i][j] = self._haversine_distance(
                        coords[i][0], coords[i][1],
                        coords[j][0], coords[j][1]
                    )
        
        return distance_matrix
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distância em km usando fórmula de Haversine"""
        R = 6371  # Raio da Terra em km
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return R * c

