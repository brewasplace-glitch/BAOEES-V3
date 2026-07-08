def test_rectangle_area():
    from project_phoenix.geometry.core.primitives_2d import Point2D, Rectangle2D
    rect = Rectangle2D(Point2D(0, 0), 4, 5)
    assert rect.area() == 20


def test_geometry_builder_counts():
    from project_phoenix.geometry.building.architectural_geometry_builder import ArchitecturalGeometryBuilder
    floorplan = {"floors": {"bg": [{"space": "A", "function": "test", "x": 0, "y": 0, "width_m": 2, "length_m": 3}]}}
    result = ArchitecturalGeometryBuilder().build_from_floorplan(floorplan)
    assert result["counts"]["spaces"] == 1
    assert result["counts"]["walls"] == 4
