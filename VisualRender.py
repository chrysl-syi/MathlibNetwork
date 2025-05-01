import plotly.graph_objects as go
import numpy, colorsys, pathlib, json
from MathlibNet import MathlibNet
from collections import defaultdict


class NetworkRenderer:
    def __init__(self, network: MathlibNet):
        self.net = network
        self.fig = go.Figure()
        
        self.activeEdges = []
        
    def render(self, outputFile='mathlib_fixed.html'):
        """"""
        self._draw_elements()
        self._configure(outputFile)
        
    def _draw_elements(self):
        """Draw nodes and edges"""
        # Nodes
        for branch, node in self.net.nodes.items():
            self._add_node(branch, node)
        
        # Edges
        for src, dst in self.activeEdges:
            self._add_edge(src, dst)
            
        # Catalog
        for cata, posi in self.net.cataPosition.items():
            self._add_catalog(cata)

    def _add_node(self, branch: str, node):
        """Draw node"""
        # x, y = node.position
        trace = go.Scatter(
            x = [node.position[0]],
            y = [node.position[1]],
            mode = "markers",
            marker = dict(
                size = node.radius * 10,
                color = node.color,
                opacity = 0.7
            ),
            text=f"<b>{branch}</b>",
            hoverinfo="text",
            customdata=[branch],
            name = branch,
        )
        self.fig.add_trace(trace)
        
    def _add_edge(self, src: str, dst: str):
        """Draw edge"""
        src_node = self.net.nodes[src]
        dst_node = self.net.nodes[dst]
        
        cx, cy = self.__sigmoid_curve(src_node.position, dst_node.position)

        trace = go.Scatter(
            x=cx,
            y=cy,
            mode="lines",
            line=dict(width=1, color=src_node.color),
            hoverinfo='none',
            showlegend=False,
        )
        self.fig.add_trace(trace)
        
    def _add_catalog(self, cata):
        """Write catalog"""
        nodeIds = [branch for branch, node in self.net.nodes.items() if node.group == cata]
        x, y = self.net.cataPosition[cata]
        trace = go.Scatter(
                x = [x],
                y = [y],
                mode="text",
                text=[f"<b>{cata}</b>"],
                textfont=dict(
                    size=20,
                    color = self.__modify_color(self.net.cataColors[cata], 0.9),
                    family="Arial"
                ),
                textposition="middle center",
                # showlegend=True,
                customdata=[nodeIds],
                marker=dict(
                    color="rgba(255,255,255,0.7)",
                    size=0,
                    opacity=0.7
                )
            )
        self.fig.add_trace(trace)
        
    def _gener_cataLegend(self):
        cataGroups = defaultdict(list)
        for nodeId, node in self.net.nodes.items():
            cataGroups[node.group].append(nodeId)
        
        buttons = []
        for catalog, nodeIds in cataGroups.items():
            buttons.append(dict(
                label=f"{catalog} ({len(nodeIds)})",
                method="restyle",
                args=[{
                    'meta.catalog_action': 'highlight',
                    'meta.catalog_name': catalog
                }],
                # 保留原始可见性控制
                args2=[{"visible": [True] * len(self.fig.data)}]
            ))
        
        buttons.insert(0, dict(
            label="All",
            method="update",
            args=[{'meta.reset_all': True}]
        ))
        
        return dict(
            type="dropdown",
            direction="down",
            x=1.1, 
            y=1,
            buttons=buttons,
            active=-1,
            font={'color': '#aaaaaa'}
        )

    def _configure(self, outputFile):
        """Configure"""
        # interaction
        self.fig.update_layout(
            dragmode="pan",
            clickmode="event",
            meta = dict(plotly_div_id = 'graph')
        )
        
        # layout
        self.fig.update_layout(
            plot_bgcolor = "black",
            paper_bgcolor = "black",
            font_color = "white",
            
            xaxis = dict(
                fixedrange = False,
                showgrid = False,
                zeroline = False,
                visible = False,
                showticklabels = False
            ),
            yaxis=dict(
                fixedrange = False,
                showgrid = False,
                zeroline = False,
                visible = False,
                showticklabels = False,
            ),
            
            updatemenus = [self._gener_cataLegend()],
        )
        
        # event
        self.fig.update_layout(
            showlegend = False,
            modebar_remove = ["lasso2d", "select", "hoverClosest"]
        )
        
        netData = {
            'nodes': {branch: {
                'group': node.group,
                'position': node.position,
                'defaultColor': node.color,
                'activeColor': self.__modify_color(node.color),
                'nextNode': list(node.nextNode),
                'prevNode': list(node.prevNode)
            } for branch, node in self.net.nodes.items()}
        }
        
        self.fig.write_html(
            outputFile,
            config = {'scrollZoom': True},
            include_plotlyjs = True,
            full_html = True,
            div_id = 'graph'
        )
        
        with open(outputFile, 'a') as f:
            f.write(f"""
            <script src="interact.js"></script>
            <script>
            initializeInteractiveNetwork({json.dumps(netData)});
            </script>
            """)
        
    def __modify_color(self, color, light=0.6, satur=0.8):
        """Modify the color"""
        hex_color = color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        new_r, new_g, new_b = colorsys.hls_to_rgb(h, light, satur)
    
        new_hex = '#%02x%02x%02x' % (
            int(new_r * 255),
            int(new_g * 255),
            int(new_b * 255)
        )
        return new_hex

    def __bezier_curve(self, p0, p1, curvature=0.7, num_points=40):
        """Generate a cubic Bezier curve"""
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        dist = numpy.sqrt(dx**2 + dy**2)
        
        nx, ny = -dy/dist, dx/dist
        
        c1x = x0 + dx/3 + curvature * dist * 0.5 * nx
        c1y = y0 + dy/3 + curvature * dist * 0.5 * ny
        c2x = x1 - dx/3 - curvature * dist * 0.5 * nx
        c2y = y1 - dy/3 - curvature * dist * 0.5 * ny
        
        t = numpy.linspace(0, 1, num_points)
        x = (1-t)**3 * x0 + 3*(1-t)**2*t * c1x + 3*(1-t)*t**2 * c2x + t**3 * x1
        y = (1-t)**3 * y0 + 3*(1-t)**2*t * c1y + 3*(1-t)*t**2 * c2y + t**3 * y1
        
        return x, y
    
    def __sigmoid_curve(self, p0, p1, steepness=5, num_points=40):
        """Generate a sigmoid curve"""
        x0, y0 = p0
        x1, y1 = p1
        t = numpy.linspace(0, 1, num_points)
        x = x0 + t * (x1 - x0)
        y = y0 + (y1 - y0) * (1 / (1 + numpy.exp(-steepness * (2*t - 1))))
        
        return x, y
