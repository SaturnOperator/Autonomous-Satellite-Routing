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
        # Update the satellite's position based on its speed
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
    def __init__(self, satellites):
        super().__init__()
        self.satellites = satellites
        self.selected_index = None  # Track selected satellite index
        self.scatter_plot = None  # Store the scatter plot item
        self.initUI()
        self.update_graph_timer = QtCore.QTimer()
        self.update_graph_timer.timeout.connect(self.update_graph)
        self.update_graph_timer.start(100)  # Update graph every 100 ms

    def initUI(self):
        # Main layout
        main_layout = QHBoxLayout()

        # 3D plot
        self.canvas = MplCanvas()
        self.plot_points()
        
        # Satellite list
        self.satellite_list = QListWidget()
        for i in range(len(self.satellites)):
            self.satellite_list.addItem(f"Satellite {i}")

        # Connect list selection to handler
        self.satellite_list.currentRowChanged.connect(self.on_satellite_selected)

        # Coordinate and Speed editor
        self.editor_widget = CoordinateEditor()
        self.editor_widget.value_changed.connect(self.update_satellite_attributes)

        # Add and delete buttons
        self.add_button = QPushButton("Add Satellite")
        self.add_button.clicked.connect(self.add_satellite)
        
        self.delete_button = QPushButton("Delete Satellite")
        self.delete_button.clicked.connect(self.delete_satellite)

        # Left side layout (list and editor)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Satellites"))
        left_layout.addWidget(self.satellite_list)
        left_layout.addWidget(self.editor_widget)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.delete_button)

        # Add widgets to main layout
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
        colors = ['red' if i == self.selected_index else 'white' for i in range(len(self.satellites))]
        coords = np.array([satellite.get_cartesian_coordinates() for satellite in self.satellites])
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color=colors, s=20)

        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color='white', linewidth=2)

        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        self.canvas.ax.set_box_aspect([1, 1, 1])
        
        self.canvas.draw()

    def on_satellite_selected(self, index):
        if index != self.selected_index:
            self.selected_index = index
            self.plot_points()  # Re-plot to update color
        if index >= 0:
            satellite = self.satellites[index]
            self.editor_widget.set_sliders(satellite.longitude, satellite.latitude, satellite.height, satellite.speed)

    def update_satellite_attributes(self, longitude, latitude, height, speed):
        if self.selected_index is not None:
            satellite = self.satellites[self.selected_index]
            satellite.longitude = longitude
            satellite.latitude = latitude
            satellite.height = height
            satellite.speed = speed
            self.plot_points()

    def add_satellite(self):
        longitude, latitude, height = np.random.uniform(0, 360), np.random.uniform(-90, 90), np.random.uniform(-0.1, 0.1)
        speed = np.random.uniform(0.5, 2.0)  # Random speed in degrees per update
        new_satellite = Satellite(longitude, latitude, height, speed)
        self.satellites.append(new_satellite)
        self.satellite_list.addItem(f"Satellite {len(self.satellites) - 1}")
        self.plot_points()

    def delete_satellite(self):
        if self.selected_index is not None:
            del self.satellites[self.selected_index]
            self.satellite_list.takeItem(self.selected_index)
            # Update selected_index to previous item if available
            if self.selected_index > 0:
                self.selected_index -= 1
            elif len(self.satellites) > 0:
                self.selected_index = 0
            else:
                self.selected_index = None
            self.plot_points()  # Re-plot without the deleted satellite
            self.update_satellite_list()

    def update_satellite_list(self):
        self.satellite_list.clear()
        for i in range(len(self.satellites)):
            self.satellite_list.addItem(f"Satellite {i}")

    def update_graph(self):
        for satellite in self.satellites:
            satellite.update_position()  # Update each satellite's position
        self.plot_points()  # Redraw with updated positions

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
        self.speed_slider = self.create_slider(0, 10, 0.1)  # Speed slider with range from 0 to 5

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
        height = self.height_slider.value() / 100.0  # Scaling down height
        speed = self.speed_slider.value()
        self.value_changed.emit(longitude, latitude, height, speed)

    def set_sliders(self, longitude, latitude, height, speed):
        self.longitude_slider.blockSignals(True)
        self.latitude_slider.blockSignals(True)
        self.height_slider.blockSignals(True)
        self.speed_slider.blockSignals(True)

        self.longitude_slider.setValue(int(longitude))
        self.latitude_slider.setValue(int(latitude))
        self.height_slider.setValue(int(height * 100))
        self.speed_slider.setValue(int(speed))

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
            speed=np.random.uniform(0.5, 1)
        ) for _ in range(num_satellites)
    ]

    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(satellites)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
