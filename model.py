import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QListWidget, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout, QPushButton, QTabWidget, QMenuBar, QAction
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from satellite import Satellite, Constellation

# Colour palette 
COLOUR_LIGHT_BLUE = "#A5A9F4"
COLOUR_GREY = "#696877"
COLOUR_BLACK = "#202020"

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
    TIMER_INTERVAL = 100
    path = []

    def __init__(self, satellites):
        super().__init__()
        self.satellites = satellites
        self.constellation = Constellation()
        self.selected_indices = []  # Track selected satellite indices
        self.scatter_plot = None
        self.pause = False  # Pause state
        self.initUI()
        self.update_graph_timer = QtCore.QTimer()
        self.update_graph_timer.timeout.connect(self.update_graph)
        self.start_timer()

    def initUI(self):
        main_layout = QHBoxLayout()

        # 3D plot
        self.canvas = MplCanvas()
        self.canvas.mpl_connect('pick_event', self.canvas_onclick) # Handles clicked nodes in graph
        self.plot_points()

        # Put plot in QWidget, round border 
        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("border-radius: 10px; background-color: black;")
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.addWidget(self.canvas)
        
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

        # Put Add/Delete buttons in same row
        add_del_buttons = QWidget()
        add_del_buttons_layout = QHBoxLayout(add_del_buttons)
        add_del_buttons_layout.addWidget(self.add_button)
        add_del_buttons_layout.addWidget(self.delete_button)
        
        # Pause toggle button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self.toggle_pause)

        # Left side layout (list, editor, and distance)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Satellites"))
        left_layout.addWidget(self.satellite_list)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.editor_widget, "Params")

        left_layout.addWidget(self.tabs)
        left_layout.addWidget(self.distance_label)
        left_layout.addWidget(add_del_buttons)
        left_layout.addWidget(self.pause_button)
        main_layout.addLayout(left_layout)
        main_layout.addWidget(self.canvas_container)

        # Create menu bar
        self.menubar = QMenuBar(self)
        main_layout.setMenuBar(self.menubar)
        distribute_menu = self.menubar.addMenu("Distribute")
        
        # Add distribution functions to menu bar
        self.dist_grid_action = QAction("Distribute to Grid")
        self.dist_grid_action.triggered.connect(self.distribute_grid)

        self.dist_spiral_action = QAction("Distribute to Spiral")
        self.dist_spiral_action.triggered.connect(self.distribute_spiral)

        self.dist_ring_action = QAction("Distribute to Ring")
        self.dist_ring_action.triggered.connect(self.distribute_ring)

        self.dist_random_action = QAction("Distribute to Random")
        self.dist_random_action.triggered.connect(self.distribute_random)

        self.dist_split_action = QAction("Distribute to Split")
        self.dist_split_action.triggered.connect(self.distribute_split)

        self.dist_cluster_action = QAction("Distribute to Cluster")
        self.dist_cluster_action.triggered.connect(self.distribute_cluster)

        self.uniform_speed_action = QAction("Set Uniform Speed")
        self.uniform_speed_action.triggered.connect(self.set_uniform_speed)

        self.random_speed_action = QAction("Set Random Speed")
        self.random_speed_action.triggered.connect(self.set_random_speed)

        distribute_menu.addAction(self.dist_grid_action)
        distribute_menu.addAction(self.dist_spiral_action)
        distribute_menu.addAction(self.dist_ring_action)
        distribute_menu.addAction(self.dist_random_action)
        distribute_menu.addAction(self.dist_split_action)
        distribute_menu.addAction(self.dist_cluster_action)
        distribute_menu.addAction(self.uniform_speed_action)
        distribute_menu.addAction(self.random_speed_action)

        # Add menu for routing
        train_menu = self.menubar.addMenu("Route")
        self.train_action = QAction("Train Q-Learning")
        self.train_action.triggered.connect(self.train_init)
        train_menu.addAction(self.train_action)
        
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
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color=colors, s=20, picker=True)

        # Plot great-circle arc if two satellites are selected
        if len(self.selected_indices) == 2:
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            arc_points = self.calculate_great_circle_arc(sat1, sat2)
            arc_x, arc_y, arc_z = zip(*arc_points)
            self.canvas.ax.plot(arc_x, arc_y, arc_z, color=COLOUR_BLUE, linestyle='--', linewidth=1) # arcline

        elif len(self.path) > 1:
            pairs = [[self.path[i], self.path[i + 1]] for i in range(len(self.path) - 1)]
            for pair in pairs:
                sat1 = pair[0]
                sat2 = pair[1]
                arc_points = self.calculate_great_circle_arc(sat1, sat2)
                arc_x, arc_y, arc_z = zip(*arc_points)
                self.canvas.ax.plot(arc_x, arc_y, arc_z, color=COLOUR_GREEN, linestyle='-', linewidth=1) # arcline


        # Draw a vertical line through the center
        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color=COLOUR_BLUE_DIM, linewidth=0.5)

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

    def pause_timer(self):
        # Pauses the update graph timer.
        self.update_graph_timer.stop()

    def start_timer(self):
        # Resumes the update graph timer.
        self.update_graph_timer.start(self.TIMER_INTERVAL)

    def canvas_onclick(self, event):
        # Selects the clicked satellite in the graph view 
        indices = event.ind # Get selected point (might be multiple if overlapping)
        modifiers = QtWidgets.QApplication.keyboardModifiers() # Check if control held
        
        if (modifiers & QtCore.Qt.ControlModifier): # Ctrl held for mutli/extended-selection
            selection = self.selected_indices[:1] + [int(indices[0])] # Append original node to clicked node
            self.satellite_list.clearSelection()
            self.selected_indices = selection # Update selection in graph view
            for i in self.selected_indices: # Update selection in list view
                self.satellite_list.item(i).setSelected(True)
        else:
            selection = int(indices[0])
            self.satellite_list.clearSelection()
            self.selected_indices = [selection] # Update selection in graph view
            self.satellite_list.item(selection).setSelected(True) # Update selection in list view

    def on_satellite_selected(self):
        self.selected_indices = [index.row() for index in self.satellite_list.selectedIndexes()]
        if len(self.selected_indices) == 2:
            self.editor_widget.setEnabled(False)
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            distance = sat1.calculate_distance(sat2)
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

    def calculate_great_circle_arc(self, sat1, sat2, num_points=50):
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
        longitude = np.random.uniform(0, 360)
        latitude = np.random.uniform(-90, 90)
        height = 0
        speed = 0.5
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
        if self.pause:
            self.pause_button.setText("Pause")
            self.pause_timer()
        else:
            self.pause_button.setText("Resume")
            self.start_timer()

    def update_graph(self):
        if not self.pause:
            for satellite in self.satellites:
                satellite.update_position()
        self.plot_points()
        if len(self.selected_indices) == 2:
            # Update the distance label if two satellites are selected
            sat1 = self.satellites[self.selected_indices[0]]
            sat2 = self.satellites[self.selected_indices[1]]
            distance = sat1.calculate_distance(sat2)
            self.distance_label.setText(f"Distance: {distance:.2f} km")

    def distribute_grid(self):
        # Grid Distribution
        n = len(self.satellites)
        num_latitudes = int(np.sqrt(n))
        num_longitudes = int(np.sqrt(n))

        latitudes = np.linspace(-90, 90, num_latitudes)
        longitudes = np.linspace(0, 360, num_longitudes, endpoint=False)
        i = 0
        for lat in latitudes:
            for lon in longitudes:
                if i < n:
                    self.satellites[i].latitude = lat
                    self.satellites[i].longitude = lon
                    i += 1
        self.plot_points()

    def distribute_spiral(self):
        # Golden Ratio Distribution
        n = len(self.satellites)
        if n < 2:
            return
        golden_angle = np.pi * (3 - np.sqrt(5))  # Approximate golden angle in radians
        for i in range(len(self.satellites)):
            self.satellites[i].latitude = np.degrees(np.arcsin(-1 + 2 * i / (n - 1)))  # Distribute latitude evenly between -90 and 90
            self.satellites[i].longitude = np.degrees((i * golden_angle) % (2 * np.pi))  # Distribute longitude based on golden angle
        self.plot_points()

    def distribute_ring(self):
        n = len(self.satellites)
        latitude = 0  # All satellites are on the equatorial plane
        longitudes = np.linspace(0, 360, n, endpoint=False)  # Evenly spaced longitudes around the ring

        for i in range(n):
            self.satellites[i].latitude = latitude
            self.satellites[i].longitude = longitudes[i]
        self.plot_points()

    def distribute_random(self):
        for i in range(len(self.satellites)):
            self.satellites[i].latitude = np.random.uniform(-90, 90)
            self.satellites[i].longitude = np.random.uniform(0, 360)
        self.plot_points()

    def distribute_split(self):
        n = len(self.satellites)
        half_n = n // 2

        if(n < 2):
            return
        
        # Top hemisphere distribution
        for i in range(half_n):
            latitude = np.random.uniform(35, 90)  # Random latitude between 0 and 90 (top hemisphere)
            longitude = np.linspace(0, 360, half_n, endpoint=False)[i % half_n]  # Evenly spaced longitudes
            self.satellites[i].latitude = latitude
            self.satellites[i].longitude = longitude
        
        # Bottom hemisphere distribution
        for i in range(half_n, n):
            latitude = np.random.uniform(-90, -35)  # Random latitude between -90 and 0 (bottom hemisphere)
            longitude = np.linspace(0, 360, half_n, endpoint=False)[i % half_n]  # Evenly spaced longitudes
            self.satellites[i].latitude = latitude
            self.satellites[i].longitude = longitude
        self.plot_points()

    def distribute_cluster(self):
        n = len(self.satellites)
        # Clustered distribution
        num_clusters = 5  # Number of clusters

        if n < num_clusters: # Handle edge case
            num_clusters = n

        satellites_per_cluster = n // num_clusters
        cluster_centers = [(np.random.uniform(-90, 90), np.random.uniform(0, 360)) for _ in range(num_clusters)]
        
        for i in range(n):
            cluster_idx = i // satellites_per_cluster
            center_lat, center_lon = cluster_centers[cluster_idx % num_clusters]
            latitude = np.random.normal(center_lat, 5)  # Cluster around the center latitude with some variance
            longitude = (np.random.normal(center_lon, 10)) % 360  # Cluster around the center longitude with some variance
            self.satellites[i].latitude = np.clip(latitude, -90, 90)  # Ensure latitude stays within bounds
            self.satellites[i].longitude = longitude
        self.plot_points()

    def set_uniform_speed(self):
        for i in range(len(self.satellites)):
            self.satellites[i].speed = 0.5

    def set_random_speed(self):
        for i in range(len(self.satellites)):
            self.satellites[i].speed = np.random.uniform(0.5, 1)

    def train_iteration(self, start_satellite, end_satellite):
        current_satellite = start_satellite
        path = [current_satellite]
        while current_satellite != end_satellite:
            state_current = current_satellite.get_state(end_satellite)
            possible_actions = current_satellite.get_possible_actions(self.satellites)
            if not possible_actions:
                # No possible actions; terminate the iteration
                break

            action_current = current_satellite.choose_action(state_current, possible_actions)
            next_satellite = action_current

            # Simulate adding a connection (increasing congestion)
            # current_satellite.connections.append(next_satellite)
            # next_satellite.connections.append(current_satellite)

            state_next = next_satellite.get_state(end_satellite)
            reward = current_satellite.get_reward(state_next, next_satellite == end_satellite)
            current_satellite.update_q_value(state_current, action_current, reward, state_next, self.satellites)

            # Simulate removing the connection (decreasing congestion)
            # current_satellite.connections.remove(next_satellite)
            # next_satellite.connections.remove(current_satellite)

            # Move to the next satellite
            current_satellite = next_satellite
            path.append(current_satellite)

            if is_final:
                break

        return path


    def train_init(self):
        if len(self.selected_indices) != 2:
            return
        
        sat1 = self.selected_indices[0]
        sat2 = self.selected_indices[1]

        self.path = self.constellation.train(self.satellites, start_index=sat1, end_index=sat2)
        print("Training complete, optimal path:", self.path)
        self.selected_indices = []
        self.satellite_list.clearSelection()

class CoordinateEditor(QWidget):
    value_changed = QtCore.pyqtSignal(float, float, float, float)
    
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        
        self.longitude_slider = self.create_slider(-180, 180, 0)
        self.latitude_slider = self.create_slider(-90, 90, 0)
        self.speed_slider = self.create_slider(0, 5, 1)

        layout.addRow(QLabel("Longitude"), self.longitude_slider)
        layout.addRow(QLabel("Latitude"), self.latitude_slider)
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
        height = 0
        speed = self.speed_slider.value()
        self.value_changed.emit(longitude, latitude, height, speed)

    def set_sliders(self, longitude, latitude, height, speed):
        # Temporarily block signals to avoid unnecessary updates
        self.longitude_slider.blockSignals(True)
        self.latitude_slider.blockSignals(True)
        self.speed_slider.blockSignals(True)

        self.longitude_slider.setValue(int(longitude))
        self.latitude_slider.setValue(int(latitude))
        self.speed_slider.setValue(int(speed))

        # Re-enable signals
        self.longitude_slider.blockSignals(False)
        self.latitude_slider.blockSignals(False)
        self.speed_slider.blockSignals(False)

def main():
    num_satellites = 100 # Initialize with 100 satellites
    satellites = [
        Satellite(
            longitude = np.random.uniform(0, 360),
            latitude = np.random.uniform(-90, 90),
            height = 0,
            speed = 0.5
        ) for _ in range(num_satellites)
    ]

    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(satellites)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
