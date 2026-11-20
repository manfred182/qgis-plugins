# -*- coding: utf-8 -*-
"""
Calculadora de geometrías y atributos espaciales
"""
import math
from ..utils.compatibility import (
    import_qgs_geometry,
    import_qgs_point_xy,
    import_qgs_wkb_types,
    log_info,
)
from .coordinate_parser import CoordinateParser, CoordinateFormat


class GeometryCalculator:

    @staticmethod
    def calculate_polygon_area_perimeter(points):
        if len(points) < 3:
            return 0.0, 0.0

        area = 0.0
        perimeter = 0.0

        for i in range(len(points)):
            j = (i + 1) % len(points)
            area += points[i].x() * points[j].y()
            area -= points[j].x() * points[i].y()

            dx = points[j].x() - points[i].x()
            dy = points[j].y() - points[i].y()
            perimeter += math.sqrt(dx * dx + dy * dy)

        area = abs(area) / 2.0
        return area, perimeter

    @staticmethod
    def calculate_point_distances(points):
        distances = [0.0]
        total_distance = 0.0

        for i in range(1, len(points)):
            p1 = points[i - 1]
            p2 = points[i]

            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist = math.sqrt(dx * dx + dy * dy)
            total_distance += dist
            distances.append(total_distance)

        return distances, total_distance

    @staticmethod
    def calculate_haversine_distances(lat_lon_pairs):
        distances = [0.0]
        total_distance = 0.0

        for i in range(1, len(lat_lon_pairs)):
            lat1, lon1 = lat_lon_pairs[i - 1]
            lat2, lon2 = lat_lon_pairs[i]
            dist = CoordinateParser.haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += dist
            distances.append(total_distance)

        return distances, total_distance

    @staticmethod
    def calculate_centroid(points):
        if not points:
            return None
        QgsPointXYCls = import_qgs_point_xy()
        cx = sum(p.x() for p in points) / len(points)
        cy = sum(p.y() for p in points) / len(points)
        return QgsPointXYCls(cx, cy)

    @staticmethod
    def calculate_bounds(points):
        if not points:
            return None
        min_x = min(p.x() for p in points)
        max_x = max(p.x() for p in points)
        min_y = min(p.y() for p in points)
        max_y = max(p.y() for p in points)
        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "width": max_x - min_x,
            "height": max_y - min_y
        }

    @staticmethod
    def get_utm_zone(lon):
        return int((lon + 180) / 6) + 1

    @staticmethod
    def get_utm_epsg(lon, lat):
        zone = GeometryCalculator.get_utm_zone(lon)
        if lat >= 0:
            return 32600 + zone
        else:
            return 32700 + zone

    @staticmethod
    def calculate_utm_for_points(points_data, geometry_type="point"):
        results = []

        for point_info in points_data:
            result = dict(point_info)

            if "latitude" in point_info and "longitude" in point_info:
                lat = point_info["latitude"]
                lon = point_info["longitude"]
                result["utm_zone"] = GeometryCalculator.get_utm_zone(lon)
                result["utm_epsg"] = GeometryCalculator.get_utm_epsg(lon, lat)

            results.append(result)

        return results

    @staticmethod
    def create_point_geometry(x, y):
        QgsGeometryCls = import_qgs_geometry()
        PointXYCls = import_qgs_point_xy()
        point = PointXYCls(x, y)
        return QgsGeometryCls.fromPointXY(point)

    @staticmethod
    def create_polygon_geometry(points):
        QgsGeometryCls = import_qgs_geometry()
        return QgsGeometryCls.fromPolygonXY([points])

    @staticmethod
    def create_line_geometry(points):
        QgsGeometryCls = import_qgs_geometry()
        return QgsGeometryCls.fromPolylineXY(points)
