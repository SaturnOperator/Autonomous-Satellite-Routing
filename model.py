import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListWidget, QSlider, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout
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

        # Left side layout (list and editor)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Coordinates"))
        left_layout.addWidget(self.coord_list)
        left_layout.addWidget(self.editor_widget)

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
        
        x, y, z = self.coords[:, 0], self.coords[:, 1], self.coords[:, 2]
        self.scatter_plot = self.canvas.ax.scatter(x, y, z, color='white', s=20)

        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color='white', linewidth=2)

        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        s