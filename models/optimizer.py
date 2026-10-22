from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .data_generator import DeliveryPoint, Vehicle


@dataclass
class RouteSolution:
    routes: List[List[int]]
    vehicle_assignments: List[int]
    total_cost: float
    total_distance: float
    total_time: float
    penalties: float
    unassigned_points: List[int]
    metrics: Dict


class VRPTWOptimizer:

    def __init__(self, distance_matrix: np.ndarray, time_matrix: np.ndarray,
                 vehicles: List[Vehicle], points: List[DeliveryPoint], depot_index: int = 0):
        self.distance_matrix = np.asarray(distance_matrix, dtype=float)
        self.time_matrix = np.asarray(time_matrix, dtype=float)
        self.vehicles = vehicles
        self.points = points
        self.depot_index = depot_index
        self.time_penalty_per_minute = 2.0
        self.max_time_violation = 120
        self.drop_penalty = 1000.0
        self.time_limit_seconds = 15
        self._validate_inputs()

    def _validate_inputs(self):
        n = len(self.points) + 1
        if not self.vehicles:
            raise ValueError('A frota deve conter pelo menos um veículo.')
        if self.distance_matrix.shape != (n, n) or self.time_matrix.shape != (n, n):
            raise ValueError('Matrizes incompatíveis com o número de entregas.')
        if not np.isfinite(self.distance_matrix).all() or not np.isfinite(self.time_matrix).all():
            raise ValueError('Distâncias e tempos devem ser finitos.')
        if (self.distance_matrix < 0).any() or (self.time_matrix < 0).any():
            raise ValueError('Distâncias e tempos não podem ser negativos.')
        if self.depot_index != 0:
            raise ValueError('O depósito deve ocupar o índice zero.')

    def solve(self) -> RouteSolution:
        manager = pywrapcp.RoutingIndexManager(len(self.points) + 1, len(self.vehicles), 0)
        routing = pywrapcp.RoutingModel(manager)
        cost_callbacks = []

        for vehicle_index, vehicle in enumerate(self.vehicles):
            def cost_callback(from_index, to_index, v=vehicle):
                origin = manager.IndexToNode(from_index)
                destination = manager.IndexToNode(to_index)
                return round(self.distance_matrix[origin, destination] * v.cost_per_km * 100)

            cost_id = routing.RegisterTransitCallback(cost_callback)
            cost_callbacks.append(cost_id)
            routing.SetArcCostEvaluatorOfVehicle(cost_id, vehicle_index)
            routing.SetFixedCostOfVehicle(round(vehicle.fixed_cost * 100), vehicle_index)

        def demand_callback(index):
            node = manager.IndexToNode(index)
            return 0 if node == 0 else int(self.points[node - 1].demand)

        demand_id = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_id, 0, [int(v.capacity) for v in self.vehicles], True, 'Capacity'
        )

        time_callbacks = []
        for vehicle in self.vehicles:
            def time_callback(from_index, to_index, v=vehicle):
                origin = manager.IndexToNode(from_index)
                destination = manager.IndexToNode(to_index)
                if origin == destination:
                    return 0
                service = 0 if origin == 0 else int(self.points[origin - 1].service_time)
                travel = self.distance_matrix[origin, destination] * 60 / v.speed_kmh
                return int(np.ceil(travel)) + service

            time_callbacks.append(routing.RegisterTransitCallback(time_callback))

        horizon = max(p.time_window_end for p in self.points) + int(self.max_time_violation) + 24 * 60 if self.points else 24 * 60
        routing.AddDimensionWithVehicleTransits(time_callbacks, horizon, horizon, False, 'Time')
        time_dim = routing.GetDimensionOrDie('Time')
        for vehicle_index in range(len(self.vehicles)):
            time_dim.CumulVar(routing.Start(vehicle_index)).SetRange(0, horizon)
            time_dim.CumulVar(routing.End(vehicle_index)).SetRange(0, horizon)

        late_cost_cents = round(self.time_penalty_per_minute * 100)
        for node, point in enumerate(self.points, 1):
            idx = manager.NodeToIndex(node)
            earliest = max(0, int(point.time_window_start))
            latest = int(point.time_window_end) + int(self.max_time_violation)
            time_dim.CumulVar(idx).SetRange(earliest, min(horizon, latest))
            time_dim.SetCumulVarSoftUpperBound(idx, int(point.time_window_end), late_cost_cents)
            routing.AddDisjunction([idx], round(self.drop_penalty * 100))

        parameters = pywrapcp.DefaultRoutingSearchParameters()
        parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        parameters.time_limit.seconds = max(1, int(self.time_limit_seconds))
        assignment = routing.SolveWithParameters(parameters)
        if assignment is None:
            raise RuntimeError('O solver não encontrou solução. Revise os parâmetros do cenário.')

        routes, assignments = [], []
        km_total, duration_total, operating_cost, late_cost = 0.0, 0.0, 0.0, 0.0
        for vehicle_index, vehicle in enumerate(self.vehicles):
            idx = routing.Start(vehicle_index)
            route = []
            route_km = 0.0
            while not routing.IsEnd(idx):
                node = manager.IndexToNode(idx)
                if node:
                    route.append(node)
                    late_minutes = max(0, assignment.Value(time_dim.CumulVar(idx)) - self.points[node - 1].time_window_end)
                    late_cost += late_minutes * self.time_penalty_per_minute
                nxt = assignment.Value(routing.NextVar(idx))
                route_km += self.distance_matrix[node, manager.IndexToNode(nxt)]
                idx = nxt
            if route:
                routes.append(route)
                assignments.append(vehicle_index)
                km_total += route_km
                operating_cost += vehicle.fixed_cost + route_km * vehicle.cost_per_km
                duration_total += assignment.Value(time_dim.CumulVar(idx)) - assignment.Value(time_dim.CumulVar(routing.Start(vehicle_index)))

        rejected = [node for node in range(1, len(self.points) + 1)
                    if assignment.Value(routing.NextVar(manager.NodeToIndex(node))) == manager.NodeToIndex(node)]
        rejection_cost = len(rejected) * self.drop_penalty
        return RouteSolution(
            routes=routes, vehicle_assignments=assignments,
            total_cost=round(operating_cost + late_cost + rejection_cost, 2),
            total_distance=round(km_total, 3), total_time=duration_total,
            penalties=round(late_cost + rejection_cost, 2), unassigned_points=rejected,
            metrics={'num_routes': len(routes), 'total_points': sum(map(len, routes)),
                     'fleet_utilization': 100 * len(routes) / len(self.vehicles),
                     'operating_cost': round(operating_cost, 2),
                     'late_penalties': round(late_cost, 2),
                     'rejection_penalties': round(rejection_cost, 2),
                     'total_distance': round(km_total, 3)}
        )
