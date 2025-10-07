import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from plotly_widget import PlotlyQtWidget
import plotly.graph_objects as go

class DemoWidget(QWidget):
    # override the event handlers to show functionality
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create layout
        layout = QVBoxLayout(self)

        # add a status label
        self.status_label = QLabel("No events yet")
        layout.addWidget(self.status_label)

        # Create web view
        self.plotly_widget = PlotlyQtWidget()
        layout.addWidget(self.plotly_widget)

        # Connect signals to slots
        self.plotly_widget.callbacks.plotly_click.connect(self.handle_plotly_click)
        self.plotly_widget.callbacks.plotly_hover.connect(self.handle_plotly_hover)
        self.plotly_widget.callbacks.plotly_selected.connect(self.handle_plotly_selected)
        self.plotly_widget.callbacks.plot_ready.connect(self.handle_plot_ready)
        self.plotly_widget.callbacks.all_plotly_events.connect(self.handle_all_events)

    def handle_all_events(self, event_type, data):
        print(f"Event: {event_type}, Data: {data}")

    def handle_plot_ready(self, message):
        print(f"Plot ready: {message}")

    def handle_plotly_click(self, data):
        event_data = json.loads(data)
        point_info = self._extract_point_info(event_data)
        self.status_label.setText(f"Clicked: {point_info}")
        print(f"Click event: {point_info}")

    def handle_plotly_hover(self, data):
        event_data = json.loads(data)
        point_info = self._extract_point_info(event_data)
        self.status_label.setText(f"Hover: {point_info}")
        print(f"Hover event: {point_info}")

    def handle_plotly_selected(self, data):
        event_data = json.loads(data)
        self.status_label.setText(f"Selection: {len(event_data.get('points', []))} points")
        print(f"Selection event: {data}")

    @staticmethod
    def _extract_point_info(event_data):
        if not event_data or 'points' not in event_data or not event_data['points']:
            return "No point data"

        point = event_data['points'][0]
        return f"x: {point.get('x')}, y: {point.get('y')}, pointNumber: {point.get('pointNumber')}"


# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle('Interactive Plotly in Qt')
    window.setGeometry(100, 100, 800, 650)

    # Create a sample plot
    fig = go.Figure(data=go.Scatter(x=[1, 2, 3, 4, 5],
                                    y=[10, 11, 12, 13, 14],
                                    mode='markers+lines',
                                    name='Test Data'))
    fig.update_layout(title='Interactive Plotly Plot')

    # Create and set the widget
    demo_widget = DemoWidget()
    demo_widget.plotly_widget.set_figure(fig)

    window.setCentralWidget(demo_widget)
    window.show()

    # Example of updating the plot after 3 seconds
    import time
    def update_plot_later():
        time.sleep(3)
        # Create a new figure with different data
        new_fig = go.Figure(data=go.Scatter(x=[1, 2, 3, 4, 5],
                                           y=[5, 7, 2, 8, 3],
                                           mode='markers+lines',
                                           name='Updated Data'))
        new_fig.update_layout(title='Updated Plotly Plot')
        demo_widget.plotly_widget.set_figure(new_fig)

    import threading
    update_thread = threading.Thread(target=update_plot_later)
    update_thread.daemon = True
    update_thread.start()

    sys.exit(app.exec())
