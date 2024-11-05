import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QListWidget, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout, QPushButton
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure(facecolor='black')
        self.ax = fig.add_subplot(111, projection='3d', frame_on=False)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        super().__init__(fig)

class SpherePlot(QWidget):
    def __init__(self, coords):
        super().__init__()
        self.coords = coords
        self.selected_index = None  # Track selected coordinate index
        self.scatter_plot = None  # Store the scatter plot item
        self.initUI()

    def initUI(self):
        # Main layout
        main_layout = QHBoxLayout()

        # 3D plot
        self.canvas = MplCanvas()
        self.plot_points()
        
        # Coordinates list
        self.coord_list = QListWidget()
        for i, coord in enumerate(self.coords):
            self.coord_list.addItem(f"Point {i}: {coord}")

        # Connect list selection to handler
        self.coord_list.currentRowChanged.connect(self.on_coordinate_selected)

        # Coordinate editor
        self.editor_widget = CoordinateEditor()
        self.editor_widget.value_changed.connect(self.update_coordinate)

        # Add and delete buttons
        self.add_button = QPushButton("Add Coordinate")
        self.add_button.clicked.connect(self.add_coordinate)
        
        self.delete_button = QPushButton("Delete Coordinate")
        self.delete_button.clicked.connect(self.delete_coordinate)

        # Left side layout (list and editor)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Coordinates"))
        left_layout.addWidget(self.coord_list)
        left_layout.addWidget(self.editor_widget)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.delete_button)

        # Add widgets to main layout
        main_layout.addLayout(left_layout)
        main_layout.addWidget(self.canvas)
        
        self.setLayout(main_layout)
        self.setWindowTitle("3D Sphere Plot with Coordinate Editor")
        self.setGeometry(100, 100, 1000, 600)
        self.show()

    def plot_points(self):
        self.canvas.ax.clear()
        self.canvas.ax.set_facecolor('black')

        # Create scatter plot
        colors = ['red' if i == self.selected_index else 'white' for i in range(len(self.coords))]
        x, y, z = self.coords[:, 0], self.coords[:, 1], self.coords[:, 2]
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color=colors, s=20)

        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color='white', linewidth=2)

        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        self.canvas.ax.set_box_aspect([1, 1, 1])
        
        self.canvas.draw()

    def on_coordinate_selected(self, index):
        if index != self.selected_index:
            self.selected_index = index
            self.plot_points()  # Re-plot to update color
        if index >= 0:
            coord = self.coords[index]
            longitude, latitude, height = self.cartesian_to_spherical(coord)
            self.editor_widget.set_sliders(longitude, latitude, height)

    def update_coordinate(self, longitude, latitude, height):
        if self.selected_index is not None:
            self.coords[self.selected_index] = self.spherical_to_cartesian(longitude, latitude, height)
            self.coord_list.item(self.selected_index).setText(f"Point {self.selected_index}: {self.coords[self.selected_index]}")
            self.plot_points()

    def add_coordinate(self):
        new_coord = generate_random_coords_on_sphere(1)[0]
        self.coords = np.vstack([self.coords, new_coord])
        self.coord_list.addItem(f"Point {len(self.coords) - 1}: {new_coord}")
        self.plot_points()

    def delete_coordinate(self):
        if self.selected_index is not None:
            self.coords = np.delete(self.coords, self.selected_index, axis=0)
            self.coord_list.takeItem(self.selected_index)
            self.selected_index = None  # Reset selection
            self.plot_points()  # Re-plot without the deleted point

    def cartesian_to_spherical(self, coord):
        # Convert Cartesian (x, y, z) to spherical (longitude, latitude, height)
        x, y, z = coord
        r = np.sqrt(x**2 + y**2 + z**2)
        longitude = np.degrees(np.arctan2(y, x))
        latitude = np.degrees(np.arcsin(z / r))
        height = r - 1  # Assume the radius of the sphere is 1
        return longitude, latitude, height

    def spherical_to_cartesian(self, longitude, latitude, height):
        # Convert spherical (longitude, latitude, height) to Cartesian (x, y, z)
        r = 1 + height  # Base radius is 1, plus the height adjustment
        lon = np.radians(longitude)
        lat = np.radians(latitude)
        x = r * np.cos(lat) * np.cos(lon)
        y = r * np.cos(lat) * np.sin(lon)
        z = r * np.sin(lat)
        return np.array([x, y, z])

class CoordinateEditor(QWidget):
    value_changed = QtCore.pyqtSignal(float, float, float)
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        
        self.longitude_slider = self.create_slider(-180, 180, 0)
        self.latitude_slider = self.create_slider(-90, 90, 0)
        self.height_slider = self.create_slider(-10, 10, 0)

        layout.addRow(QLabel("Longitude"), self.longitude_slider)
        layout.addRow(QLabel("Latitude"), self.latitude_slider)
        layout.addRow(QLabel("Height"), self.height_slider)
        
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
        # Emit the values from sliders for longitude, latitude, and height
        longitude = self.longitude_slider.value()
        latitude = self.latitude_slider.value()
        height = self.height_slider.value() / 100.0  # Scaling down height
        self.value_changed.emit(longitude, latitude, height)

    def set_sliders(self, longitude, latitude, height):
        # Temporarily block signals to avoid triggering updates unnecessarily
        self.longitude_slider.blockSignals(True)
        self.latitude_slider.blockSignals(True)
        self.height_slider.blockSignals(True)

        self.longitude_slider.setValue(int(longitude))
        self.latitude_slider.setValue(int(latitude))
        self.height_slider.setValue(int(height * 100))

        # Re-enable signals
        self.longitude_slider.blockSignals(False)
        self.latitude_slider.blockSignals(False)
        self.height_slider.blockSignals(False)

def generate_random_coords_on_sphere(num_points):
    theta = np.random.uniform(0, 2 * np.pi, num_points)
    phi = np.random.uniform(-np.pi / 2, np.pi / 2, num_points)
    x = np.cos(phi) * np.cos(theta)
    y = np.cos(phi) * np.sin(theta)
    z = np.sin(phi)
    return np.column_stack((x, y, z))

def main():
    num_points = 100  # For simplicity, using a smaller number of points
    coords = generate_random_coords_on_sphere(num_points)

    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(coords)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
