import numpy as np

from models.data_generator import DataGenerator
from models.optimizer import VRPTWOptimizer
from utils.metrics import MetricsCalculator
from utils.visualization import RouteVisualizer


def test_route_visualization_and_metrics():
    generator = DataGenerator(seed=42)
    points = generator.generate_delivery_points(12)
    fleet = generator.generate_fleet(2, 3)
    distance = generator.calculate_distance_matrix(points, generator.city_center)
    optimizer = VRPTWOptimizer(distance, distance * 60 / 40, fleet, points)
    optimizer.time_limit_seconds = 2
    result = optimizer.solve()
    assigned = [fleet[i] for i in result.vehicle_assignments]
    visualizer = RouteVisualizer(*generator.city_center)
    assert visualizer.create_map(result.routes, points, assigned, result.metrics) is not None
    metrics = MetricsCalculator.calculate_kpi_metrics(result.routes, points, assigned, distance, result.penalties)
    assert metrics['total_routes'] == len(result.routes)
    assert np.isclose(metrics['total_distance'], result.total_distance, atol=1e-3)
    assert len(result.unassigned_points) + metrics['total_points_delivered'] == len(points)
