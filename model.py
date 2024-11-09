import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QListWidget, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout, QPushButton
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from satellite import Satellite

# Colour palette 
COLOUR_LIGHT_BLUE = "#A5A9F4"
COLUR_GREY = "#696877"

COLOUR_WHITE = "#CCC9E8"
COLOUR_WHITE_DIM = "#5D5E6E"

COLOUR_RED = "#D44557"
COLOUR_RED_DIM = "#352A42"

COLOUR_BLUE = "#698EF7"
COLOUR_BLUE_DIM = "#252A3B"

COLOUR_GREEN = "#6CE999"
COLOUR_GREEN_DIM = "#22392E"

COLOUR_PURPLE ="#895DD0"
COLOUR_PURPLE_DIM = "#352647"

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
        self.great_circle_line = None  # Line to represent the great-circle arc
        self.pause = False  # Pause state
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

        # Pause toggle button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self.toggle_pause)

        # Left side layout (list, editor, and distance)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Satellites"))
        left_layout.addWidget(self.satellite_list)
        left_layout.addWidget(self.editor_widget)
        left_layout.addWidget(self.distance_label)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.delete_button)
        left_layout.addWidget(self.pause_button)

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
        colors = [COLOUR_RED if i in self.selected_indices else COLOUR_WHITE for i in range(len(self.satellites))]
        coords = np.array([satellite.get_cartesian_coordinates() for satellite in self.satellites])
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color=colors, s=20)

        # Plot great-circle arc if two satellites are selected
        if len(self.selected_indices) == 2:
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            arc_points = self.calculate_great_circle_arc(sat1, sat2)
            arc_x, arc_y, arc_z = zip(*arc_points)
            self.canvas.ax.plot(arc_x, arc_y, arc_z, color=COLOUR_BLUE, linestyle='--', linewidth=1) # arcline

        # Draw a vertical line through the center
        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color=COLOUR_BLUE_DIM, linewidth=0.5)

        # Plot Sphere in centre
        # u = np.linspace(0, 2 * np.pi, 20) # 15 segments, relatively low
        # v = np.linspace(0, np.pi, 10) 
        # sphere_radius = 0.90  # You can adjust the radius accordingly
        # sphere_x = sphere_radius * np.outer(np.cos(u), np.sin(v))
        # sphere_y = sphere_radius * np.outer(np.sin(u), np.sin(v))
        # sphere_z = sphere_radius * np.outer(np.ones(np.size(u)), np.cos(v))
        # self.canvas.ax.plot_surface(sphere_x, sphere_y, sphere_z, color=COLOUR_BLUE_DIM, alpha=0.33)

        # Plot the 2D circle
        ring_theta = np.linspace(0, 2 * np.pi, 50)
        ring_radius = 1 # You can adjust the ring_radius accordingly
        ring_x = ring_radius * np.cos(ring_theta)
        ring_y = ring_radius * np.sin(ring_theta)
        ring_z = np.zeros_like(ring_theta)  # The circle lies in the XY plane
        self.canvas.ax.plot(ring_x, ring_y, ring_z, color=COLOUR_BLUE_DIM, linewidth=0.5)

        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        self.canvas.ax.set_box_aspect([1, 1, 1])
        
        self.canvas.draw()

    def on_satellite_selected(self):
        self.selected_indices = [index.row() for index in self.satellite_list.selectedIndexes()]
        if len(self.selected_indices) == 2:
            self.editor_widget.setEnabled(False)
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            distance = self.calculate_distance(sat1, sat2)
            self.distance_label.setText(f"Distance: {distance:.2f} km")
        else:
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
        lat1, lon1 = np.radians([sat1.latitude, sat1.longitude])
        lat2, lon2 = np.radians([sat2.latitude, sat2.longitude])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        return self.EARTH_RADIUS_KM * c

    def calculate_great_circle_arc(self, sat1, sat2, num_points=100):
        # Convert lat/lon to radians
        lat1, lon1 = np.radians([sat1.latitude, sat1.longitude])
        lat2, lon2 = np.radians([sat2.latitude, sat2.longitude])

        # Calculate the angle between the two points
        d = np.arccos(np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(lon2 - lon1))

        # Calculate points along the great circle
        arc_points = []
        for t in np.linspace(0, 1, num_points):
            A = np.sin((1 - t) * d) / np.sin(d)
            B = np.sin(t * d) / np.sin(d)
            x = A * np.cos(lat1) * np.cos(lon1) + B * np.cos(lat2) * np.cos(lon2)
            y = A * np.cos(lat1) * np.sin(lon1) + B * np.cos(lat2) * np.sin(lon2)
            z = A * np.sin(lat1) + B * np.sin(lat2)
            arc_points.append((x, y, z))
        return arc_points

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

    def toggle_pause(self, checked):
        self.pause = checked
        self.pause_button.setText("Resume" if self.pause else "Pause")

    def update_graph(self):
        if not self.pause:
            for satellite in self.satellites:
                satellite.update_position()
        self.plot_points()
        if len(self.selected_indices) == 2:
            # Update the distance label if two satellites are selected
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
        self.height_slider = self.create_slider(0, 5, 0)
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
    num_satellites = 100 # Initialize with 100 satellites
    satellites = [
        Satellite(
            longitude=np.random.uniform(0, 360),
            latitude=np.random.uniform(-90, 90),
            height=0, #np.random.uniform(-0.1, 0.1),
            speed=np.random.uniform(0.5, 2.0)
        ) for _ in range(num_satellites)
    ]

    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(satellites)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
