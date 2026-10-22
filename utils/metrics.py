"""Reporting helpers for the routing application."""
from typing import Dict, List

import numpy as np
import pandas as pd


class MetricsCalculator:
    @staticmethod
    def calculate_kpi_metrics(routes: List[List[int]], points: List, vehicles: List,
                              distance_matrix: np.ndarray, penalties: float) -> Dict:
        route_distances = []
        for route in routes:
            nodes = [0, *route, 0]
            route_distances.append(sum(distance_matrix[a, b] for a, b in zip(nodes, nodes[1:])))
        num_stops = sum(map(len, routes))
        return {
            'total_routes': len(routes),
            'total_points_delivered': num_stops,
            'total_demand': sum(points[p - 1].demand for route in routes for p in route),
            'fleet_utilization': 100 * len(routes) / len(vehicles) if vehicles else 0,
            'avg_points_per_route': num_stops / len(routes) if routes else 0,
            'total_penalties': penalties,
            'penalty_per_delivery': penalties / num_stops if num_stops else 0,
            'avg_distance_per_route': float(np.mean(route_distances)) if route_distances else 0,
            'total_distance': sum(route_distances),
        }

    @staticmethod
    def create_comparison_table(solutions: List[Dict]) -> pd.DataFrame:
        return pd.DataFrame(solutions)
