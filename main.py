from MathlibNet import MathlibNet 
from VisualRender import NetworkRenderer

# Dataset Path
pathStr = "E:\program\MathlibExplorer\project\Mathlib"

MathNet = MathlibNet(pathStr)
MathNet.create()
MathNet.generNetwork()
MathNet.generVisualData()

renderer = NetworkRenderer(MathNet)
renderer.render('Visualization.html')