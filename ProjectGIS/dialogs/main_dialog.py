# -*- coding: utf-8 -*-
"""
Interfaz de usuario del plugin ProjectGIS
Version simplificada para maxima compatibilidad con QGIS 3.x - 4.x
"""
import os
from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QGroupBox, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QTabWidget,
    QWidget
)

from ..utils.crs_utils import AUTO_DETECT_CRS_LABEL


class ProjectGISDialog(QDialog):
    file_selected = pyqtSignal(str)
    process_complete = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ProjectGIS - Excel a Shapefile/GeoPackage")
        self.setMinimumSize(750, 680)
        self.setModal(True)

        self._selected_file = None
        self._selected_sheets = []
        self._headers = []
        self._preview_data = []

        self._plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ========== HEADER CON LOGO ==========
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        self.logo_label = QLabel()
        logo_path = os.path.join(self._plugin_dir, 'logo_header.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.logo_label.setPixmap(
                pixmap.scaled(QSize(140, 140), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.logo_label.setText("ProjectGIS")
            self.logo_label.setStyleSheet(
                "font-size: 20px; font-weight: bold; color: #2980b9;"
            )
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setFixedWidth(150)
        header_layout.addWidget(self.logo_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("ProjectGIS")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        title_layout.addWidget(title)

        subtitle = QLabel("Convierte tablas de coordenadas Excel a Shapefile/GeoPackage")
        subtitle.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        title_layout.addWidget(subtitle)

        version_label = QLabel("v1.0.2")
        version_label.setStyleSheet("font-size: 10px; color: #b2bec3;")
        title_layout.addWidget(version_label)

        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Separador
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #dcdde1;")
        main_layout.addWidget(line)

        # ========== TABS ==========
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_file_tab(), "1. Archivo Excel")
        self.tabs.addTab(self._create_config_tab(), "2. Configuracion")
        self.tabs.addTab(self._create_export_tab(), "3. Exportar")
        self.tabs.addTab(self._create_preview_tab(), "4. Vista Previa")
        main_layout.addWidget(self.tabs)

        # ========== BARRA DE PROGRESO ==========
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        # ========== BOTONES INFERIORES ==========
        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setMinimumWidth(100)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_process = QPushButton("Procesar")
        self.btn_process.setMinimumWidth(150)
        self.btn_process.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; padding: 8px 20px; }"
            "QPushButton:hover { background-color: #2ecc71; }"
        )
        btn_layout.addWidget(self.btn_process)

        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _create_file_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Seleccion de archivo
        grp_file = QGroupBox("Seleccionar Archivo Excel")
        grp_file_layout = QHBoxLayout()

        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("Seleccione un archivo .xlsx o .xlsm...")
        self.txt_file_path.setReadOnly(True)
        grp_file_layout.addWidget(self.txt_file_path)

        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.btn_browse.setMinimumWidth(100)
        grp_file_layout.addWidget(self.btn_browse)

        grp_file.setLayout(grp_file_layout)
        layout.addWidget(grp_file)

        # Hojas
        grp_sheets = QGroupBox("Hojas del Archivo (Ctrl+Click para seleccionar varias)")
        grp_sheets_layout = QVBoxLayout()

        self.lst_sheets = QtWidgets.QListWidget()
        self.lst_sheets.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.lst_sheets.setMinimumHeight(130)
        self.lst_sheets.setMaximumHeight(180)
        grp_sheets_layout.addWidget(self.lst_sheets)

        sheets_btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Seleccionar Todas")
        self.btn_select_all.setMinimumWidth(120)
        sheets_btn_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deseleccionar Todas")
        self.btn_deselect_all.setMinimumWidth(130)
        sheets_btn_layout.addWidget(self.btn_deselect_all)

        sheets_btn_layout.addStretch()
        grp_sheets_layout.addLayout(sheets_btn_layout)

        grp_sheets.setLayout(grp_sheets_layout)
        layout.addWidget(grp_sheets)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Formato de coordenadas
        grp_coord = QGroupBox("Formato de Coordenadas")
        coord_grid = QGridLayout()

        coord_grid.addWidget(QLabel("Formato de entrada:"), 0, 0)
        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "Auto-detectar",
            "Grados Decimales (Lon, Lat)",
            "UTM (X, Y)",
            "Grados Minutos Segundos (DMS)"
        ])
        coord_grid.addWidget(self.cmb_format, 0, 1)

        coord_grid.addWidget(QLabel("Columna X / Longitud:"), 1, 0)
        self.cmb_x_col = QComboBox()
        coord_grid.addWidget(self.cmb_x_col, 1, 1)

        coord_grid.addWidget(QLabel("Columna Y / Latitud:"), 2, 0)
        self.cmb_y_col = QComboBox()
        coord_grid.addWidget(self.cmb_y_col, 2, 1)

        coord_grid.addWidget(QLabel("Columna Z (opcional):"), 3, 0)
        self.cmb_z_col = QComboBox()
        self.cmb_z_col.addItem("(Ninguna)")
        coord_grid.addWidget(self.cmb_z_col, 3, 1)

        grp_coord.setLayout(coord_grid)
        layout.addWidget(grp_coord)

        # CRS
        grp_crs = QGroupBox("Sistema de Coordenadas (CRS)")
        crs_grid = QGridLayout()

        crs_grid.addWidget(QLabel("CRS de salida:"), 0, 0)
        self.cmb_crs = QComboBox()
        crs_grid.addWidget(self.cmb_crs, 0, 1)

        grp_crs.setLayout(crs_grid)
        layout.addWidget(grp_crs)

        # Calculos
        grp_calc = QGroupBox("Calculos Espaciales")
        calc_layout = QVBoxLayout()

        self.chk_calculate_utm_zone = QCheckBox("Zona UTM automatica")
        self.chk_calculate_utm_zone.setChecked(True)
        calc_layout.addWidget(self.chk_calculate_utm_zone)

        self.chk_calculate_distance = QCheckBox("Distancia entre puntos")
        calc_layout.addWidget(self.chk_calculate_distance)

        self.chk_calculate_area = QCheckBox("Area y perimetro (poligonos)")
        calc_layout.addWidget(self.chk_calculate_area)

        self.chk_calculate_centroid = QCheckBox("Centroide")
        calc_layout.addWidget(self.chk_calculate_centroid)

        grp_calc.setLayout(calc_layout)
        layout.addWidget(grp_calc)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_export_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Formatos
        grp_formats = QGroupBox("Formatos de Salida")
        fmt_layout = QVBoxLayout()

        self.chk_export_shp = QCheckBox("Shapefile (.shp)")
        self.chk_export_shp.setChecked(True)
        fmt_layout.addWidget(self.chk_export_shp)

        self.chk_export_gpkg = QCheckBox("GeoPackage (.gpkg)")
        self.chk_export_gpkg.setChecked(True)
        fmt_layout.addWidget(self.chk_export_gpkg)

        self.chk_export_csv = QCheckBox("CSV (.csv)")
        fmt_layout.addWidget(self.chk_export_csv)

        grp_formats.setLayout(fmt_layout)
        layout.addWidget(grp_formats)

        # Carpeta de salida
        grp_output = QGroupBox("Carpeta de Salida")
        output_layout = QHBoxLayout()

        self.txt_output_dir = QLineEdit()
        self.txt_output_dir.setPlaceholderText("Seleccione carpeta de salida...")
        self.txt_output_dir.setReadOnly(True)
        output_layout.addWidget(self.txt_output_dir)

        self.btn_browse_output = QPushButton("Examinar...")
        self.btn_browse_output.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.btn_browse_output.setMinimumWidth(100)
        output_layout.addWidget(self.btn_browse_output)

        grp_output.setLayout(output_layout)
        layout.addWidget(grp_output)

        # Nombre
        grp_name = QGroupBox("Nombre de Capa")
        name_layout = QHBoxLayout()

        name_layout.addWidget(QLabel("Nombre:"))
        self.txt_layer_name = QLineEdit("coordenadas_convertidas")
        name_layout.addWidget(self.txt_layer_name)

        grp_name.setLayout(name_layout)
        layout.addWidget(grp_name)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_preview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        lbl = QLabel("Vista previa de los datos:")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        self.table_preview = QTableWidget()
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_preview)

        widget.setLayout(layout)
        return widget

    def _connect_signals(self):
        self.btn_browse.clicked.connect(self._on_browse_file)
        self.btn_browse_output.clicked.connect(self._on_browse_output)
        self.btn_select_all.clicked.connect(self._on_select_all_sheets)
        self.btn_deselect_all.clicked.connect(self._on_deselect_all_sheets)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_process.clicked.connect(self._on_process)
        self.lst_sheets.itemSelectionChanged.connect(self._on_sheets_changed)

    def _on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo Excel", "",
            "Archivos Excel (*.xlsx *.xlsm);;Todos (*)"
        )
        if file_path:
            self._selected_file = file_path
            self.txt_file_path.setText(file_path)
            self.file_selected.emit(file_path)

    def _on_browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Salida"
        )
        if dir_path:
            self.txt_output_dir.setText(dir_path)

    def _on_select_all_sheets(self):
        for i in range(self.lst_sheets.count()):
            self.lst_sheets.item(i).setSelected(True)

    def _on_deselect_all_sheets(self):
        self.lst_sheets.clearSelection()

    def _on_sheets_changed(self):
        selected = self.lst_sheets.selectedItems()
        self._selected_sheets = [item.text() for item in selected]

    def _on_process(self):
        if not self._selected_file:
            QMessageBox.warning(self, "Archivo Requerido",
                "Seleccione un archivo Excel.")
            return
        if not self._selected_sheets:
            QMessageBox.warning(self, "Hojas Requeridas",
                "Seleccione al menos una hoja.")
            return
        if not self.txt_output_dir.text():
            QMessageBox.warning(self, "Carpeta Requerida",
                "Seleccione una carpeta de salida.")
            return
        if (not self.chk_export_shp.isChecked() and
            not self.chk_export_gpkg.isChecked() and
            not self.chk_export_csv.isChecked()):
            QMessageBox.warning(self, "Formato Requerido",
                "Seleccione al menos un formato de salida.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.process_complete.emit(True, "Procesando...")

    def set_sheets(self, sheet_names):
        self.lst_sheets.clear()
        for name in sheet_names:
            self.lst_sheets.addItem(name)

    def set_column_names(self, headers):
        self._headers = headers
        self.cmb_x_col.clear()
        self.cmb_y_col.clear()
        self.cmb_z_col.clear()
        self.cmb_z_col.addItem("(Ninguna)")
        for h in headers:
            self.cmb_x_col.addItem(h)
            self.cmb_y_col.addItem(h)
            self.cmb_z_col.addItem(h)
        if len(headers) > 0:
            self.cmb_x_col.setCurrentIndex(0)
        if len(headers) > 1:
            self.cmb_y_col.setCurrentIndex(1)

    def set_preview_data(self, headers, rows):
        self._preview_data = rows
        self.table_preview.setColumnCount(len(headers))
        self.table_preview.setRowCount(min(len(rows), 10))
        self.table_preview.setHorizontalHeaderLabels(headers)
        for i, row in enumerate(rows[:10]):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                self.table_preview.setItem(i, j, item)
        self.table_preview.resizeColumnsToContents()

    def set_crs_list(self, crs_names):
        self.cmb_crs.clear()
        self.cmb_crs.addItem(AUTO_DETECT_CRS_LABEL)
        for name in crs_names:
            self.cmb_crs.addItem(name)
        self.cmb_crs.setCurrentIndex(0)

    def get_config(self):
        return {
            "file_path": self._selected_file,
            "sheets": self._selected_sheets,
            "x_column": self.cmb_x_col.currentIndex(),
            "y_column": self.cmb_y_col.currentIndex(),
            "z_column": self.cmb_z_col.currentIndex() - 1
                       if self.cmb_z_col.currentIndex() > 0 else None,
            "format": self.cmb_format.currentIndex(),
            "crs": self.cmb_crs.currentText(),
            "export_shp": self.chk_export_shp.isChecked(),
            "export_gpkg": self.chk_export_gpkg.isChecked(),
            "export_csv": self.chk_export_csv.isChecked(),
            "output_dir": self.txt_output_dir.text(),
            "layer_name": self.txt_layer_name.text(),
            "calculate_area": self.chk_calculate_area.isChecked(),
            "calculate_distance": self.chk_calculate_distance.isChecked(),
            "calculate_utm_zone": self.chk_calculate_utm_zone.isChecked(),
            "calculate_centroid": self.chk_calculate_centroid.isChecked(),
        }

    def set_status(self, message):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "Info", message)

    def set_error(self, message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", message)

    def set_success(self, message):
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Exito", message)
