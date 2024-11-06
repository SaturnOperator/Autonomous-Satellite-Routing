import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QListWidget, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout, QPushButton
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class Satellite:
    def __init__(self, longitude, latitude, height, speed):
        self.longitude = longitude
        self.latitude = latitude
        self.height = height
        self.speed = speed  # Speed in degrees per update cycle
    
    def update_position(self):
        self.longitude = (self.longitude + self.speed) % 360  # Wrap longitude within 0-360 degrees

    def get_cartesian_coordinates(self):
        # Convert spherical (longitude, latitude, height) to Cartesian (x, y, z)
        r = 1 + self.height  # Assume base radius is 1
        lon = np.radians(self.longitude)
        lat = np.radians(self.latitude)
        x = r * np.cos(lat) * np.cos(lon)
        y = r * np.cos(lat) * np.sin(lon)
        z = r * np.sin(lat)
        return np.array([x, y, z])

class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure(facecolor='black')
        self.ax = fig.add_subplot(111, projection='3d', frame_on=False)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        super().__init__(fig)

class SpherePlot(QWidget):
    EARTH_RADIUS_KM = 6371  # Radius of Earth in kilometers

    def __init__(self, satellites):
        super().__init__()
        self.satellites = satellites
        self.selected_indices = []  # Track selected satellite indices
        self.scatter_plot = None
        self.initUI()
        self.update_graph_timer = QtCore.QTimer()
        self.update_graph_timer.timeout.connect(self.update_graph)
        self.update_graph_timer.start(100)

    def initUI(self):
        main_layout = QHBoxLayout()

        # 3D plot
        self.canvas = MplCanvas()
        self.plot_points()
        
        # Satellite list with multi-selection
        self.satellite_list = QListWidget()
        self.satellite_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        for i in range(len(self.satellites)):
            self.satellite_list.addItem(f"Satellite {i}")

        # Connect list selection to handler
        self.satellite_list.itemSelectionChanged.connect(self.on_satellite_selected)

        # Coordinate and Speed editor
        self.editor_widget = CoordinateEditor()
        self.editor_widget.value_changed.connect(self.update_satellite_attributes)

        # Distance display
        self.distance_label = QLabel("Distance: N/A")

        # Add and delete buttons
        self.add_button = QPushButton("Add Satellite")
        self.add_button.clicked.connect(self.add_satellite)
        
        self.delete_button = QPushButton("Delete Satellite")
        self.delete_button.clicked.connect(self.delete_satellite)

        # Left side layout (list, editor, and distance)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Satellites"))
        left_layout.addWidget(self.satellite_list)
        left_layout.addWidget(self.editor_widget)
        left_layout.addWidget(self.distance_label)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.delete_button)

        main_layout.addLayout(left_layout)
        main_layout.addWidget(self.canvas)
        
        self.setLayout(main_layout)
        self.setWindowTitle("3D Sphere Plot with Satellite Editor")
        self.setGeometry(100, 100, 1000, 600)
        self.show()

    def plot_points(self):
        self.canvas.ax.clear()
        self.canvas.ax.set_facecolor('black')

        # Plot each satellite's position
        colors = ['red' if i in self.selected_indices else 'white' for i in range(len(self.satellites))]
        coords = np.array([satellite.get_cartesian_coordinates() for satellite in self.satellites])
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color=colors, s=20)

        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color='white', linewidth=0.5)

        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        self.canvas.ax.set_box_aspect([1, 1, 1])
        
        self.canvas.draw()

    def on_satellite_selected(self):
        self.selected_indices = [index.row() for index in self.satellite_list.selectedIndexes()]
        if len(self.selected_indices) == 2:
            # Disable sliders and calculate the distance
            self.editor_widget.setEnabled(False)
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            distance = self.calculate_distance(sat1, sat2)
            self.distance_label.setText(f"Distance: {distance:.2f} km")
        else:
            # Enable sliders if not exactly two satellites are selected
            self.editor_widget.setEnabled(True)
            self.distance_label.setText("Distance: N/A")
            if len(self.selected_indices) == 1:
                satellite = self.satellites[self.selected_indices[0]]
                self.editor_widget.set_sliders(satellite.longitude, satellite.latitude, satellite.height, satellite.speed)

        self.plot_points()

    def update_satellite_attributes(self, longitude, latitude, height, speed):
        if len(self.selected_indices) == 1:
            satellite = self.satellites[self.selected_indices[0]]
            satellite.longitude = longitude
            satellite.latitude = latitude
            satellite.height = height
            satellite.speed = speed
            self.plot_points()

    def calculate_distance(self, sat1, sat2):
        # Calculate great-circle distance (haversine formula) between two latitude/longitude points
        lat1, lon1 = np.radians([sat1.latitude, sat1.longitude])
        lat2, lon2 = np.radians([sat2.latitude, sat2.longitude])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return self.EARTH_RADIUS_KM * c

    def add_satellite(self):
        longitude, latitude, height = np.random.uniform(0, 360), np.random.uniform(-90, 90), np.random.uniform(-0.1, 0.1)
        speed = np.random.uniform(0.5, 2.0)
        new_satellite = Satellite(longitude, latitude, height, speed)
        self.satellites.append(new_satellite)
        self.satellite_list.addItem(f"Satellite {len(self.satellites) - 1}")
        self.plot_points()

    def delete_satellite(self):
        if self.selected_indices:
            for index in sorted(self.selected_indices, reverse=True):
                del self.satellites[index]
                self.satellite_list.takeItem(index)
            self.selected_indices = []
            self.plot_points()
            self.update_satellite_list()

    def update_satellite_list(self):
        self.satellite_list.clear()
        for i in range(len(self.satellites)):
            self.satellite_list.addItem(f"Satellite {i}")

    def update_graph(self):
        for satellite in self.satellites:
            satellite.update_position()
        self.plot_points()
        if len(self.selected_indices) == 2:
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            distance = self.calculate_distance(sat1, sat2)
            self.distance_label.setText(f"Distance: {distance:.2f} km")

class CoordinateEditor(QWidget):
    value_changed = QtCore.pyqtSignal(float, float, float, float)
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        
        self.longitude_slider = self.create_slider(-180, 180, 0)
        self.latitude_slider = self.create_slider(-90, 90, 0)
        self.height_slider = self.create_slider(-10, 10, 0)
        self.speed_slider = self.create_slider(0, 5, 1)

        layout.addRow(QLabel("Longitude"), self.longitude_slider)
        layout.addRow(QLabel("Latitude"), self.latitude_slider)
        layout.addRow(QLabel("Height"), self.height_slider)
        layout.addRow(QLabel("Speed"), self.speed_slider)
        
        self.setLayout(layout)

    def create_slider(self, min_value, max_value, initial_value):
        slider = QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(min_value)
        slider.setMaximum(max_value)
        slider.setValue(initial_value)
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.emit_value)
        return slider

    def emit_value(self):
        longitude = self.longitude_slider.value()
        latitude = self.latitude_slider.value()
        height = self.height_slider.value() / 100.0  # Scale down height
        speed = self.speed_slider.value()
        self.value_changed.emit(longitude, latitude, height, speed)

    def set_sliders(self, longitude, latitude, height, speed):
        # Temporarily block signals to avoid unnecessary updates
        self.longitude_slider.blockSignals(True)
        self.latitude_slider.blockSignals(True)
        self.height_slider.blockSignals(True)
        self.speed_slider.blockSignals(True)

        self.longitude_slider.setValue(int(longitude))
        self.latitude_slider.setValue(int(latitude))
        self.height_slider.setValue(int(height * 100))
        self.speed_slider.setValue(int(speed))

        # Re-enable signals
        self.longitude_slider.blockSignals(False)
        self.latitude_slider.blockSignals(False)
        self.height_slider.blockSignals(False)
        self.speed_slider.blockSignals(False)

def main():
    num_satellites = 100  # Initialize with 5 satellites
    satellites = [
        Satellite(
            longitude=np.random.uniform(0, 360),
            latitude=np.random.uniform(-90, 90),
            height=np.random.uniform(-0.1, 0.1),
            speed=np.random.uniform(0.5, 2.0)
        ) for _ in range(num_satellites)
    ]

    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(satellites)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()