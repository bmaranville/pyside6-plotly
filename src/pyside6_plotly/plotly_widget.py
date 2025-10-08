import json
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
import plotly.offline

class PlotlyCallbacks(QObject):
    # Signal to update the plot: sent from Python to JS with new plot data
    update_plot = Signal(str)

    # Signal to indicate the plot is ready, sent from JS to Python
    plot_ready = Signal(str)

    # Signals for all Plotly events: sent from JS to Python
    plotly_click = Signal(str)
    plotly_legendclick = Signal(str)
    plotly_selecting = Signal(str)
    plotly_selected = Signal(str)
    plotly_hover = Signal(str)
    plotly_unhover = Signal(str)
    plotly_legenddoubleclick = Signal(str)
    plotly_restyle = Signal(str)
    plotly_relayout = Signal(str)
    plotly_webglcontextlost = Signal(str)
    plotly_afterplot = Signal(str)
    plotly_autosize = Signal(str)
    plotly_deselect = Signal(str)
    plotly_doubleclick = Signal(str)
    plotly_redraw = Signal(str)
    plotly_animated = Signal(str)

    # catch-all signal: sent from JS to Python with all event data
    all_plotly_events = Signal(str, str)  # event type, data

    @Slot(str)
    def on_plot_ready(self, message):
        self.plot_ready.emit(message)

    @Slot(str, str)
    def on_plotly_event(self, event_type, data):
        """Generic slot that handles all Plotly events"""
        # Get the signal attribute by name
        signal_attr = getattr(self, event_type, None)
        if signal_attr and hasattr(signal_attr, 'emit'):
            signal_attr.emit(data)
        self.all_plotly_events.emit(event_type, data)

    @Slot(result=str)
    def get_plotlyjs(self):
        """ Plotly.js is too big to be sent as a data url, so provide it via this method """
        return plotly.offline.get_plotlyjs()


class PlotlyQtWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set up web channel for communication
        self.channel = QWebChannel()
        self.callbacks = PlotlyCallbacks()
        self.channel.registerObject("callbacks", self.callbacks)
        self.page().setWebChannel(self.channel)

        # Flag to track if the plot has been initialized
        self.plot_initialized = False


    def initialize_plot(self, fig):
        """Initialize the plot for the first time"""
        # Convert plotly figure to JSON
        plot_json = json.dumps(fig.to_plotly_json())

        # Create HTML content with the plot and embedded Plotly.js
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
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
                let callbacks;
                const plotData = {plot_json};
                const plotDiv = document.getElementById('plot');

                document.addEventListener("DOMContentLoaded", function() {{
                    new QWebChannel(qt.webChannelTransport, async function(channel) {{
                        callbacks = channel.objects.callbacks;

                        // Load Plotly.js dynamically
                        const plotlyScript = document.createElement('script');
                        plotlyScript.type = 'text/javascript';
                        plotlyScript.text = await callbacks.get_plotlyjs();
                        document.head.appendChild(plotlyScript);

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
                                    // remove elements of event and points that are not serializable
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
                                    if (callbacks) callbacks.on_plotly_event?.(name, JSON.stringify(args));
                                }});
                            }}
                        }};

                        // Create the plot
                        Plotly.react('plot', plotData.data, plotData.layout)
                            .then(function() {{
                                callbacks.on_plot_ready("Plot initialized");

                                set_handlers(plotDiv);

                                // Listen for plot updates
                                callbacks.update_plot.connect(function(plotDataJson) {{
                                    const newPlotData = JSON.parse(plotDataJson);
                                    Plotly.react(plotDiv, newPlotData.data, newPlotData.layout, {{ responsive: true }});
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

        self.setHtml(html_content)
        self.html_content = html_content
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

        # Send the update signal with the new plot data
        self.callbacks.update_plot.emit(plot_json)

