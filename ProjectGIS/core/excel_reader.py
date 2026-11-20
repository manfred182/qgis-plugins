# -*- coding: utf-8 -*-
"""
Lector de archivos Excel (.xlsx) usando openpyxl
"""
import os
import re

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from ..utils.compatibility import log_info, log_error, log_warning


class ExcelReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.workbook = None
        self._validate_file()

    def _validate_file(self):
        if not HAS_OPENPYXL:
            raise ImportError(
                "openpyxl no esta instalado. "
                "Instale openpyxl con: pip install openpyxl"
            )
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {self.file_path}")
        if not self.file_path.lower().endswith(('.xlsx', '.xlsm')):
            raise ValueError("Solo se admiten archivos .xlsx o .xlsm")

    def open(self):
        self.workbook = openpyxl.load_workbook(self.file_path, read_only=True, data_only=True)
        log_info(f"Archivo Excel abierto: {self.file_path}")
        return self

    def close(self):
        if self.workbook:
            self.workbook.close()
            self.workbook = None

    def get_sheet_names(self):
        if not self.workbook:
            self.open()
        return self.workbook.sheetnames

    def read_sheet(self, sheet_name=None, max_rows=None):
        if not self.workbook:
            self.open()

        if sheet_name is None:
            sheet_name = self.workbook.sheetnames[0]

        ws = self.workbook[sheet_name]
        rows = []
        headers = None

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if max_rows and i > max_rows:
                break
            if i == 0:
                headers = [str(h) if h is not None else f"Col_{j}" for j, h in enumerate(row)]
            else:
                if any(cell is not None for cell in row):
                    rows.append(list(row))

        if headers is None:
            headers = [f"Col_{i}" for i in range(ws.max_column or 1)]

        log_info(f"Leidas {len(rows)} filas de hoja '{sheet_name}'")
        return headers, rows

    def read_all_sheets(self, max_rows=None):
        if not self.workbook:
            self.open()

        sheets_data = {}
        for name in self.workbook.sheetnames:
            headers, rows = self.read_sheet(name, max_rows)
            sheets_data[name] = {"headers": headers, "rows": rows}

        return sheets_data

    def preview(self, sheet_name=None, max_rows=10):
        headers, rows = self.read_sheet(sheet_name, max_rows)
        return headers, rows

    def detect_coordinate_columns(self, headers, sample_rows):
        coord_keywords_x = [
            'x', 'lon', 'long', 'longitud', 'east', 'este', 'easting',
            'x_utm', 'coord_x', 'cx', 'longitude'
        ]
        coord_keywords_y = [
            'y', 'lat', 'latitud', 'north', 'norte', 'northing',
            'y_utm', 'coord_y', 'cy', 'latitude'
        ]
        coord_keywords_z = [
            'z', 'alt', 'altura', 'elevacion', 'elevation',
            'height', 'h'
        ]

        x_col = None
        y_col = None
        z_col = None
        header_lower = [str(h).lower().strip() for h in headers]

        for i, h in enumerate(header_lower):
            tokens = set(re.split(r'[^a-z0-9]+', h)) - {''}
            for kw in coord_keywords_x:
                if kw == h or kw in tokens:
                    x_col = i
                    break
            for kw in coord_keywords_y:
                if kw == h or kw in tokens:
                    y_col = i
                    break
            for kw in coord_keywords_z:
                if kw == h or kw in tokens:
                    z_col = i
                    break

        if x_col is None and y_col is None and len(headers) >= 2:
            for i, h in enumerate(header_lower):
                if 'utm' in h or 'x' in h:
                    x_col = i
                elif 'utm' in h or 'y' in h:
                    y_col = i

        if x_col is None and y_col is None and sample_rows:
            numeric_cols = []
            for col_idx in range(len(headers)):
                is_numeric = True
                for row in sample_rows[:5]:
                    val = row[col_idx] if col_idx < len(row) else None
                    if val is not None:
                        try:
                            float(str(val).replace(',', '.'))
                        except (ValueError, TypeError):
                            is_numeric = False
                            break
                if is_numeric:
                    numeric_cols.append(col_idx)

            if len(numeric_cols) >= 2:
                x_col = numeric_cols[0]
                y_col = numeric_cols[1]

        log_info(
            f"Columnas detectadas - X: {headers[x_col] if x_col is not None else 'N/A'}, "
            f"Y: {headers[y_col] if y_col is not None else 'N/A'}, "
            f"Z: {headers[z_col] if z_col is not None else 'N/A'}"
        )
        return x_col, y_col, z_col

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
