import sys
import json
from PySide6.QtCore import QObject, Signal, Slot
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
    
    # Signal to update the plot
    update_plot = Signal(str)

    @Slot(str)
    def plotly_click(self, data):
        self.point_clicked.emit(data)
    
    @Slot(str)
    def plotly_hover(self, data):
        self.point_hovered.emit(data)
    
    @Slot(str)
    def plotly_selected(self, data):
        self.selection_changed.emit(data)
    
    @Slot(str)
    def plot_ready(self, message):
        print(f"Plot ready: {message}")

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
        # Load Plotly.js from CDN
        self.plotly_js_url = "https://cdn.plot.ly/plotly-3.0.1.min.js"

        
        # Flag to track if the plot has been initialized
        self.plot_initialized = False
        
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
    
    def initialize_plot(self, fig):
        """Initialize the plot for the first time"""
        # Convert plotly figure to JSON
        plot_json = json.dumps(fig.to_plotly_json())
        # plot_json = json.dumps({
        #     'data': fig.data,
        #     'layout': fig.layout
        # }, cls=go.Figure.get_plotly_json_encoder())
        
        # Create HTML content with the plot and embedded Plotly.js
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <script src="{self.plotly_js_url}"></script>
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
                var plotDiv = document.getElementById('plot');
                
                document.addEventListener("DOMContentLoaded", function() {{
                    new QWebChannel(qt.webChannelTransport, function(channel) {{
                        callbacks = channel.objects.callbacks;
                        // plotDiv.innerHTML = Object.keys(callbacks);

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

                        // Create the plot
                        Plotly.react('plot', plotData.data, plotData.layout)
                            .then(function() {{
                                callbacks.plot_ready("Plot initialized");

                                set_handlers(plotDiv);
                                
                                // Set up event listeners
                                //plotDiv.on('plotly_click', function(data) {{
                                //    callbacks.on_click(JSON.stringify(data));
                                //}});
                                
                                //plotDiv.on('plotly_hover', function(data) {{
                                //    callbacks.on_hover(JSON.stringify(data));
                                //}});
                                
                                //plotDiv.on('plotly_selected', function(data) {{
                                //    callbacks.on_selection(JSON.stringify(data));
                                //}});
                                
                                // Listen for plot updates
                                callbacks.update_plot.connect(function(plotDataJson) {{
                                    var newPlotData = JSON.parse(plotDataJson);
                                    Plotly.react(plotDiv, newPlotData.data, newPlotData.layout, {{ responsive: true }});
                                    //plotDiv.innerHTML = plotDataJson;
                                }});
                            }});
                    }});
                }});
            </script>
        </body>
        </html>
        '''

        # Load the HTML content directly
        with open("test.html", "w") as f:
            f.write(html_content)

        self.web_view.setHtml(html_content)
        self.plot_initialized = True
        
    def set_figure(self, fig):
        """Set or update the figure"""
        if not self.plot_initialized:
            self.initialize_plot(fig)
        else:
            self.update_figure(fig)
    
    def update_figure(self, fig):
        """Update an existing plot with new data"""
        # Convert plotly figure to JSON
        plot_json = json.dumps(fig.to_plotly_json())
        # plot_json = json.dumps({
        #     'data': fig.data,
        #     'layout': fig.layout
        # }, cls=go.Figure.get_plotly_json_encoder())
        
        # Send the update signal with the new plot data
        self.callbacks.update_plot.emit(plot_json)

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
        plot_widget.set_figure(new_fig)
    
    import threading
    update_thread = threading.Thread(target=update_plot_later)
    update_thread.daemon = True
    update_thread.start()
    
    sys.exit(app.exec())
