import sys
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from functools import partial
from PySide6.QtCore import QUrl, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
import plotly.graph_objects as go
import plotly.offline

class PlotlyCallbacks(QObject):
    # Define signals for different Plotly events
    point_clicked = Signal(str)
    point_hovered = Signal(str)
    selection_changed = Signal(str)

    @Slot(str)
    def plotly_click(self, data):
        self.point_clicked.emit(data)
    
    @Slot(str)
    def plotly_hover(self, data):
        self.point_hovered.emit(data)
    
    @Slot(str)
    def plotly_selected(self, data):
        self.selection_changed.emit(data)

class PlotlyServer(BaseHTTPRequestHandler):
    def __init__(self, plot_json, *args, **kwargs):
        self.plot_json = plot_json
        # Get Plotly.js content from the Python library
        self.plotly_js = plotly.offline.get_plotlyjs()
        super().__init__(*args, **kwargs)
        

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <script>
                    {self.plotly_js}
                </script>
                <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            </head>
            <body>
                <div id="plot"></div>
                <script>
                    // Initialize Qt web channel
                    var callbacks;
                    new QWebChannel(qt.webChannelTransport, function(channel) {{
                        callbacks = channel.objects.callbacks;
                    }});
                    
                    // Load and render the plot

                    function set_handlers(el) {{
                        // forward events
                        for (const name of [
                            // source: https://plotly.com/javascript/plotlyjs-events/
                            "plotly_click",
                            "plotly_legendclick",
                            "plotly_selecting",
                            "plotly_selected",
                            "plotly_hover",
                            "plotly_unhover",
                            "plotly_legenddoubleclick",
                            "plotly_restyle",
                            "plotly_relayout",
                            "plotly_webglcontextlost",
                            "plotly_afterplot",
                            "plotly_autosize",
                            "plotly_deselect",
                            "plotly_doubleclick",
                            "plotly_redraw",
                            "plotly_animated",
                        ]) {{
                            el.on(name, (event) => {{
                                const args = {{
                                    ...event,
                                    points: event?.points?.map((p) => ({{
                                    ...p,
                                    fullData: undefined,
                                    xaxis: undefined,
                                    yaxis: undefined,
                                    }})),
                                    xaxes: undefined,
                                    yaxes: undefined,
                                }};
                                if (callbacks) callbacks[name]?.(JSON.stringify(args));
                            }});
                        }}
                    }};
                    fetch('/plot-data')
                        .then(response => response.json())
                        .then(data => {{
                            var plot = Plotly.react('plot', data.data, data.layout);
                            
                            const el = document.getElementById('plot');
                            set_handlers(el);
                            // Set up event listeners
                            //document.getElementById('plot').on('plotly_click', function(data) {{
                            //    if (callbacks) callbacks.on_click(JSON.stringify(data));
                            //}});
                            
                            //document.getElementById('plot').on('plotly_hover', function(data) {{
                            //    if (callbacks) callbacks.on_hover(JSON.stringify(data));
                            //}});
                            
                            //document.getElementById('plot').on('plotly_selected', function(data) {{
                            //    if (callbacks) callbacks.on_selection(JSON.stringify(data));
                            //}});
                        }});
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
            
        elif self.path == '/plot-data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(self.plot_json.encode())
            
        elif self.path == '/plotly.min.js':
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript')
            self.end_headers()
            
            plotly_js = plotly.offline.get_plotly_js()
            # import requests
            # plotly_js = requests.get('https://cdn.plot.ly/plotly-3.0.1.min.js').content
            self.wfile.write(plotly_js)
        else:
            self.send_response(404)
            self.end_headers()

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class PlotlyQtWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = None
        self.server_thread = None
        self.port = None
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create web view
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # Create status label
        self.status_label = QLabel("No events yet")
        layout.addWidget(self.status_label)

        # Get Plotly.js content from the Python library
        self.plotly_js = plotly.offline.get_plotlyjs()
        
        # Set up web channel for communication
        self.channel = QWebChannel()
        self.callbacks = PlotlyCallbacks()
        self.channel.registerObject("callbacks", self.callbacks)
        self.web_view.page().setWebChannel(self.channel)
        
        # Connect signals to slots
        self.callbacks.point_clicked.connect(self.handle_click)
        self.callbacks.point_hovered.connect(self.handle_hover)
        self.callbacks.selection_changed.connect(self.handle_selection)

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
        plot_json = json.dumps(fig.to_plotly_json())
        # plot_json = json.dumps({
        #     'data': fig.data,
        #     'layout': fig.layout
        # }, cls=go.Figure.get_plotly_json_encoder())
        
        # Stop existing server if running
        self.stop_server()
        
        # Start new server
        self.port = find_free_port()
        handler = partial(PlotlyServer, plot_json)
        self.server = HTTPServer(('localhost', self.port), handler)
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Load the plot in the web view
        self.web_view.load(QUrl(f'http://localhost:{self.port}'))
    
    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join()
            self.server = None
            self.server_thread = None
    
    def closeEvent(self, event):
        self.stop_server()
        super().closeEvent(event)

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
