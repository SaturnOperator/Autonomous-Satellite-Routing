import sys
import numpy as np
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure()
        self.ax = fig.add_subplot(111, projection='3d')
        super().__init__(fig)

class SpherePlot(QtWidgets.QWidget):
    def __init__(self, coords):
        super().__init__()
        self.initUI(coords)

    def initUI(self, coords):
        # Set up the matplotlib canvas
        self.canvas = MplCanvas()
        self.plot_points(coords)

        # Layout for the widget
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setWindowTitle("3D Spherical Plot")
        self.setGeometry(100, 100, 800, 600)
        self.show()

    def plot_points(self, coords):
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]

        # Set background color
        self.canvas.ax.set_facecolor('black')

        # Plot points in white
        self.canvas.ax.scatter(x, y, z, color='white', s=20)

        # Draw a vertical line through the center of the sphere
        vertical_line_x = [0, 0]
        vertical_line_y = [0, 0]
        vertical_line_z = [-1, 1]
        self.canvas.ax.plot(vertical_line_x, vertical_line_y, vertical_line_z, color='white', linewidth=2)

        # Hide grid, axis lines, and labels
        self.canvas.ax.grid(False)
        self.canvas.ax.set_axis_off()
        self.canvas.ax.set_xticks([])
        self.canvas.ax.set_yticks([])
        self.canvas.ax.set_zticks([])

        # Make the plot look spherical
        self.canvas.ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

def generate_random_coords_on_sphere(num_points):
    # Generate random spherical coordinates and convert to Cartesian
    theta = np.random.uniform(0, 2 * np.pi, num_points)
    phi = np.random.uniform(0, np.pi, num_points)
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack((x, y, z))

def main():
    num_points = 100  # Number of points to plot
    coords = generate_random_coords_on_sphere(num_points)

    # Initialize the PyQt5 application
    app = QtWidgets.QApplication(sys.argv)
    main_window = SpherePlot(coords)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
