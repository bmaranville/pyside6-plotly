"""Main module."""
import sys
import json
from PySide6.QtCore import QUrl, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript
import plotly.graph_objects as go
import plotly.offline

class PlotlyCallbacks(QObject):
    # Define signals for different Plotly events
    point_clicked = Signal(str)
    point_hovered = Signal(str)
    selection_changed = Signal(str)

    @Slot(str)
    def on_click(self, data):
        self.point_clicked.emit(data)
    
    @Slot(str)
    def on_hover(self, data):
        self.point_hovered.emit(data)
    
    @Slot(str)
    def on_selection(self, data):
        self.selection_changed.emit(data)

class PlotlyQtWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create web view
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Create status label
        self.status_label = QLabel("No events yet")
        layout.addWidget(self.status_label)
        
        # Set up web channel for communication
        self.channel = QWebChannel()
        self.callbacks = PlotlyCallbacks()
        self.channel.registerObject("callbacks", self.callbacks)
        self.web_view.page().setWebChannel(self.channel)
        
        # Connect signals to slots
        self.callbacks.point_clicked.connect(self.handle_click)
        self.callbacks.point_hovered.connect(self.handle_hover)
        self.callbacks.selection_changed.connect(self.handle_selection)
        
        # Get Plotly.js content from the Python library
        self.plotly_js = plotly.offline.get_plotlyjs()

        
    def handle_click(self, data):
        event_data = json.loads(data)
        point_info = self.extract_point_info(event_data)
        self.status_label.setText(f"Clicked: {point_info}")
        print(f"Click event: {point_info}")
    
    def handle_hover(self, data):
        event_data = json.loads(data)
        point_info = self.extract_point_info(event_data)
        self.status_label.setText(f"Hover: {point_info}")
        print(f"Hover event: {point_info}")
    
    def handle_selection(self, data):
        event_data = json.loads(data)
        self.status_label.setText(f"Selection: {len(event_data.get('points', []))} points")
        print(f"Selection event: {data}")
    
    def extract_point_info(self, event_data):
        if not event_data or 'points' not in event_data or not event_data['points']:
            return "No point data"
        
        point = event_data['points'][0]
        return f"x: {point.get('x')}, y: {point.get('y')}, pointNumber: {point.get('pointNumber')}"
        
    def set_figure(self, fig):
        # Convert plotly figure to JSON
        plot_json = json.dumps({
            'data': fig.data,
            'layout': fig.layout
        }, cls=go.Figure.get_plotly_json_encoder())
        
        # Create HTML content with the plot
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <script>
                {self.plotly_js}
            </script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                body, html {{ margin: 0; padding: 0; height: 100%; }}
                #plot {{ width: 100%; height: 100%; }}
            </style>
        </head>
        <body>
            <div id="plot"></div>
            <script>
                // Initialize Qt web channel
                var callbacks;
                var plotData = {plot_json};
                
                document.addEventListener("DOMContentLoaded", function() {{
                    new QWebChannel(qt.webChannelTransport, function(channel) {{
                        callbacks = channel.objects.callbacks;
                        
                        // Create the plot
                        Plotly.newPlot('plot', plotData.data, plotData.layout);
                        
                        // Set up event listeners
                        document.getElementById('plot').on('plotly_click', function(data) {{
                            callbacks.on_click(JSON.stringify(data));
                        }});
                        
                        document.getElementById('plot').on('plotly_hover', function(data) {{
                            callbacks.on_hover(JSON.stringify(data));
                        }});
                        
                        document.getElementById('plot').on('plotly_selected', function(data) {{
                            callbacks.on_selection(JSON.stringify(data));
                        }});
                    }});
                }});
            </script>
        </body>
        </html>
        '''
        
        # Load the HTML content directly
        self.web_view.setHtml(html_content)

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
    plot_widget = PlotlyQtWidget()
    plot_widget.set_figure(fig)
    
    window.setCentralWidget(plot_widget)
    window.show()
    
    sys.exit(app.exec())
