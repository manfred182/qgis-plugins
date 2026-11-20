# -*- coding: utf-8 -*-
"""
Parser de coordenadas en múltiples formatos:
- Grados decimales
- UTM
- Grados, minutos, segundos (DMS)
"""
import re
import math
from ..utils.compatibility import log_info, log_warning


class CoordinateFormat:
    DECIMAL = "decimal"
    UTM = "utm"
    DMS = "dms"
    AUTO = "auto"


class CoordinateParser:
    ZONE_KEYWORDS = ['zona_utm', 'utm_zone', 'huso', 'zona']

    DMS_PATTERN = re.compile(
        r'(\d{1,3})\s*[°º]\s*(\d{1,2})\s*[\'\u2032]\s*'
        r'(\d{1,2}(?:[.,]\d+)?)\s*["\u2033]\s*([NSEWnsew])'
    )
    DMS_PATTERN2 = re.compile(
        r'(\d{1,3})\s+(\d{1,2})\s+(\d{1,2}(?:[.,]\d+)?)\s+([NSEWnsew])'
    )

    @staticmethod
    def dms_to_decimal(degrees, minutes, seconds, direction):
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if direction.upper() in ('S', 'W'):
            decimal = -decimal
        return decimal

    @staticmethod
    def decimal_to_dms(decimal_val):
        direction = 'E' if decimal_val >= 0 else 'W'
        abs_val = abs(decimal_val)
        degrees = int(abs_val)
        minutes_float = (abs_val - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        return degrees, minutes, seconds, direction

    @staticmethod
    def detect_format(value_str):
        value_str = str(value_str).strip()

        if not value_str:
            return None, None

        value_str_clean = value_str.replace(',', '.')

        dms_match = CoordinateParser.DMS_PATTERN.search(value_str)
        if dms_match:
            return CoordinateFormat.DMS, value_str

        dms_match2 = CoordinateParser.DMS_PATTERN2.search(value_str)
        if dms_match2:
            return CoordinateFormat.DMS, value_str

        try:
            val = float(value_str_clean)
            return CoordinateFormat.DECIMAL, val
        except ValueError:
            pass

        parts = re.split(r'[\s,\t]+', value_str_clean)
        if len(parts) >= 2:
            try:
                x = float(parts[0])
                y = float(parts[1])
                return CoordinateFormat.UTM, (x, y)
            except ValueError:
                pass

        return None, None

    @staticmethod
    def parse_dms(dms_str):
        match = CoordinateParser.DMS_PATTERN.search(dms_str)
        if match:
            deg = int(match.group(1))
            minutes = int(match.group(2))
            sec = float(match.group(3).replace(',', '.'))
            direction = match.group(4)
            return CoordinateParser.dms_to_decimal(deg, minutes, sec, direction)

        match = CoordinateParser.DMS_PATTERN2.search(dms_str)
        if match:
            deg = int(match.group(1))
            minutes = int(match.group(2))
            sec = float(match.group(3).replace(',', '.'))
            direction = match.group(4)
            return CoordinateParser.dms_to_decimal(deg, minutes, sec, direction)

        return None

    @staticmethod
    def parse_value(value, source_crs_format=CoordinateFormat.AUTO):
        if value is None:
            return None

        val_str = str(value).strip()
        if not val_str:
            return None

        if source_crs_format == CoordinateFormat.AUTO:
            fmt, parsed = CoordinateParser.detect_format(val_str)
        elif source_crs_format == CoordinateFormat.DMS:
            fmt = CoordinateFormat.DMS
            parsed = val_str
        elif source_crs_format == CoordinateFormat.UTM:
            fmt = CoordinateFormat.UTM
            try:
                val_clean = val_str.replace(',', '.')
                parts = re.split(r'[\s,\t]+', val_clean)
                if len(parts) >= 2:
                    parsed = (float(parts[0]), float(parts[1]))
                else:
                    parsed = float(val_clean)
            except ValueError:
                return None
        else:
            fmt = CoordinateFormat.DECIMAL
            try:
                parsed = float(val_str.replace(',', '.'))
            except ValueError:
                return None

        if fmt == CoordinateFormat.DMS:
            return CoordinateParser.parse_dms(parsed)
        elif fmt == CoordinateFormat.DECIMAL:
            return parsed
        elif fmt == CoordinateFormat.UTM:
            if isinstance(parsed, tuple):
                return parsed
            return None

        return None

    @staticmethod
    def parse_coordinate_pair(x_value, y_value, z_value=None,
                               source_format=CoordinateFormat.AUTO):
        x = CoordinateParser.parse_value(x_value, source_format)
        y = CoordinateParser.parse_value(y_value, source_format)

        if x is None or y is None:
            return None

        if isinstance(x, tuple) and isinstance(y, tuple):
            return {
                "type": CoordinateFormat.UTM,
                "x": x[0],
                "y": y[0] if len(y) > 0 else 0,
                "zone": int((x[0] + 180) / 6) + 1 if abs(x[0]) < 180 else None,
                "z": z_value
            }
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            is_utm = abs(x) > 360 or abs(y) > 360
            if is_utm:
                return {
                    "type": CoordinateFormat.UTM,
                    "x": x,
                    "y": y,
                    "zone": None,
                    "z": z_value
                }
            else:
                return {
                    "type": CoordinateFormat.DECIMAL,
                    "x": x,
                    "y": y,
                    "z": z_value
                }

        return None

    @staticmethod
    def is_valid_geographic_degrees(x, y):
        return abs(x) <= 180 and abs(y) <= 90

    @staticmethod
    def find_zone_column(headers, exclude_cols=None):
        exclude_cols = exclude_cols or set()
        header_lower = [str(h).lower().strip() for h in headers]
        for i, h in enumerate(header_lower):
            if i in exclude_cols:
                continue
            tokens = set(re.split(r'[^a-z0-9]+', h)) - {''}
            for kw in CoordinateParser.ZONE_KEYWORDS:
                if kw == h or kw in tokens:
                    return i
        return None

    @staticmethod
    def parse_zone_value(raw):
        if raw is None:
            return None
        s = str(raw).strip().upper()
        match = re.match(r'^(\d{1,2})(?:\.0+)?\s*([NS]?)$', s)
        if not match:
            return None
        zone = int(match.group(1))
        if zone < 1 or zone > 60:
            return None
        hemisphere = match.group(2) or 'N'
        return zone, hemisphere

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def euclidean_distance(x1, y1, x2, y2):
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
