from pathlib import Path
from typing import List, Dict, Set, Optional
import colorsys, os, networkx, numpy
import matplotlib.pyplot as plt
from collections import defaultdict

from LeanFileNode import LeanFileNode

class MathlibNet:
    def __init__(self, filePath: str):
        """
        Net of Mathlib
        
        param:
            filePath: Path of Mathlib under root directory
        """
        self.filePath = Path(filePath)
        self.nodes: Dict[str, LeanFileNode] = {}
        self.catalog: List[str] = []
        self.cataPosition = {}
        self.cataColors = {}
        self.DAGnet = networkx.DiGraph()
        self.ignore: List[str] = [
            "Control",
            "Tactic",
            "Util",
            
            # "Algebra",
            # "AlgebraicGeometry",
            # "Analysis",
            # "CategortTheory"
            # "Condensed",
            # "Data",
            # "Dynamics",
            # "FieldTheory",
            # "Geometry",
            # "Order",
            # "RingTheory",
            # "SetTheory",
            # "Topology",
        ]
        
        self.forceIgnore: List[str] = [
            "Lean",
            "Std",
            "Testing",
            "Init.lean",
            "Tactic.lean",
            "Deprecated",
            ]
    
    def create(self):
        """Build net"""
        leanFiles = list(self.filePath.glob('**/*.lean'))
        
        # Create nodes
        for file in leanFiles:
            node = LeanFileNode(file)
            self.nodes[node.branch] = node
            
        # Read catalog
        dirs = [name for name in os.listdir(self.filePath) 
              if os.path.isdir(os.path.join(self.filePath, name))]
        self.catalog = dirs
        
        # Build net
        for node in self.nodes.values():
            for depend in node.depends:
                if depend in self.nodes:
                    node.addNode_prev(depend)
                    self.nodes[depend].addNode_next(node.branch)
                    
        self.applyIgnore(self.forceIgnore)
    
    def generNetwork(self):
        """Get networkx object"""
        G = networkx.DiGraph()
        for branch, node in self.nodes.items():
            G.add_node(branch, **{
                'def_count': node.contents['def'],
                'theorem_count': node.contents['theorem'],
                'lemma_count': node.contents['lemma'],
            })
            
            for next in node.nextNode:
                if next in self.nodes:
                    G.add_edge(branch, next)
        self.DAGnet = G
        print(f'#Nodes: {G.number_of_nodes()}')
        print(f'#Edges: {G.number_of_edges()}')
        
    def generVisualData(self):
        G = self.DAGnet
        
        # Topological sort & Depends closure
        topoSort = list(networkx.topological_sort(G))
        topoIndex = {node: i for i, node in enumerate(topoSort)}
        
        depeClosure = [set(networkx.ancestors(G, node)) for node in topoSort]
        horizontal_position = [len(depeClosure[i]) ** 0.72 for i in range(len(depeClosure))]
        vertical_position = [0 for i in range(len(depeClosure))]
        
        # Allocate attributes
        # Catalog
        catalogDict = {group: idx for idx, group in enumerate(self.catalog)}
        cataColors = self._gener_colors(len(self.catalog))
        cataPosiY = numpy.linspace(50, 250, len(self.catalog))
        self.cataColors = dict(zip(self.catalog, cataColors))
        
        # Position
        stacks = {i: set() for i in range(-50, 1000)} # Deal the stacked cases
        # Deal x position
        horizontal_minus = 0 # Use x-minus to set start nodes
        for i in range(len(topoSort)):
            if horizontal_position[i] == 0:
                horizontal_position[i] = -horizontal_minus
                horizontal_minus = (horizontal_minus + 1) % 10
            stacks[int(horizontal_position[i])].add(i)
        # Deal y position
        for i, stack in stacks.items():
            isVertical = [False for i in range(300)]
            for node in stack:
                depeNodes = [tar for tar in G.predecessors(topoSort[node]) 
                        if self.nodes[tar].group == self.nodes[topoSort[node]]]
                sum_y = vertical_position[node]
                for each in depeNodes:
                    sum_y += vertical_position[topoIndex[each]]
                avg_y = sum_y / (1 + len(depeNodes))
                
                blankSlot = 0
                while isVertical[int(avg_y + self.__get_drift(blankSlot))]:
                    blankSlot += 1
                vertical_position[node] = avg_y + self.__get_drift(blankSlot)
                isVertical[int(vertical_position[node])] = True
                
        # Weight
        # weight = networkx.pagerank(G)
        # weight = networkx.pagerank(G.to_undirected())
        weight = networkx.pagerank(G.reverse())
        weight_max = max(weight.values())
        weight_min = min(weight.values())
        
        # Update
        for branch, index in topoIndex.items():
            node = self.nodes[branch]
            if node.group in catalogDict:
                cataIndex = catalogDict[node.group]
                node.color = cataColors[cataIndex]
            node.radius = self.__get_radius(weight[branch], weight_max, weight_min)
            posiBaseY = cataPosiY[cataIndex]
            node.position = [horizontal_position[index], posiBaseY + vertical_position[index]]
        self._calculate_cataPosition()    
            
    def applyIgnore(self, list = []):
        """Ignore unrelated files"""
        # Update catalog
        if not list:
            list = self.ignore
        raw = self.catalog
        self.catalog = [item for item in raw if item not in list]

        # Ignore unrelated files
        ignorance = self._parse_ignore(list)
        for tar in ignorance:
            node = self.nodes[tar]
            for pred in node.prevNode:
                if pred in self.nodes:
                    self.nodes[pred].nextNode.discard(tar)
            for succ in node.nextNode:
                if succ in self.nodes:
                    self.nodes[succ].prevNode.discard(tar)
            del self.nodes[tar]
     
    def _calculate_cataPosition(self):
        """"""
        catalog_groups = defaultdict(list)
        
        for node in self.nodes.values():
            catalog_groups[node.group].append(node.position)
        
        for catalog, positions in catalog_groups.items():
            if positions:
                avg_x = sum(p[0] for p in positions) / len(positions)
                avg_y = sum(p[1] for p in positions) / len(positions)
                self.cataPosition[catalog] = (avg_x, avg_y)
        
    def _gener_colors(self, N: int, light=0.2, satur=0.8) -> List:
        colors = []
        for i in range(N):
            hue = i / N  # 均匀分布色相
            r, g, b = colorsys.hls_to_rgb(hue, light, satur)
            hex_color = '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))
            colors.append(hex_color)
        return colors[::2] + colors[1::2]
    
    def _parse_ignore(self, list) -> List:
        """Parse all ignored files"""
        filePath = self.filePath
        # list = self.ignore
        
        result = []
        for tar in list:
            tarPath = filePath / tar
            if not tarPath.exists():
                continue
            if tarPath.is_file() and tarPath.suffix == '.lean':
                result.append(tar.rsplit('.', 1)[0])
            elif tarPath.is_dir():
                for file in tarPath.rglob("*"):
                    if not file.is_file() or file.suffix != '.lean':
                        continue
                    relPath = file.relative_to(filePath).with_suffix('')
                    branch = str(relPath).replace('\\', '.').replace('/', '.')
                    result.append(branch)
        return result
    
    def __get_drift(self, a):
        dy = a // 2
        derc = 1 if a % 2 == 0 else -1
        return derc * dy
    
    def __get_radius(self, val, vmax, vmin):
        return 0.2 + 3 * ((val - vmin) / (vmax - vmin)) ** 0.5
    
    def __repr__(self):
        return f"<Nodes: {self.DAGnet.number_of_nodes()}, Edges: {self.DAGnet.number_of_edges()}>"
