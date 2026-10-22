import numpy as np
from models.data_generator import Vehicle, DeliveryPoint
from models.optimizer import VRPTWOptimizer


def test_vehicle_cost_and_return_to_depot():
    points = [DeliveryPoint(1, 0.0, 0.0, 1, 480, 600, 5, 1)]
    vehicles = [Vehicle(0, 'car', 5, 2.0, 10.0, 60.0, 0.1)]
    distances = np.array([[0, 2], [2, 0]], dtype=float)
    optimizer = VRPTWOptimizer(distances, distances, vehicles, points)
    optimizer.time_limit_seconds = 2
    result = optimizer.solve()
    assert result.routes == [[1]]
    assert result.unassigned_points == []
    assert result.total_distance == 4
    assert result.total_cost == 18


def test_infeasible_capacity_rejects_delivery():
    points = [DeliveryPoint(1, 0.0, 0.0, 20, 480, 600, 5, 1)]
    vehicles = [Vehicle(0, 'motorcycle', 5, 1.0, 2.0, 40.0, 0.05)]
    distances = np.array([[0, 1], [1, 0]], dtype=float)
    optimizer = VRPTWOptimizer(distances, distances, vehicles, points)
    optimizer.time_limit_seconds = 2
    result = optimizer.solve()
    assert result.unassigned_points == [1]
    assert result.routes == []
    assert result.total_cost == optimizer.drop_penalty
