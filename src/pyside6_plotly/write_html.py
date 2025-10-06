import plotly.graph_objs as go
from plotly.offline import plot, get_plotlyjs
fig1 = go.Figure(data=[{'type': 'bar', 'y': [1, 3, 2]}],
                 layout={'height': 400})
fig2 = go.Figure(data=[{'type': 'scatter', 'y': [1, 3, 2]}],
                  layout={'height': 400})
div1 = plot(fig1, output_type='div', include_plotlyjs=False)
div2 = plot(fig2, output_type='div', include_plotlyjs=False)
html = '''
<html>
    <head>
        <script type="text/javascript">{plotlyjs}</script>
    </head>
    <body>
       {div1}
       {div2}
    </body>
</html>
'''.format(plotlyjs=get_plotlyjs(), div1=div1, div2=div2)
with open('multi_plot.html', 'w') as f:
     f.write(html) # doctest: +SKIP