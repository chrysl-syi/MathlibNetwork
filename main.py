from MathlibNet import MathlibNet 
from VisualRender import NetworkRenderer

# Dataset Path
pathStr = "**\Mathlib"

MathNet = MathlibNet(pathStr)
MathNet.create()
MathNet.generNetwork()
MathNet.generVisualData()

renderer = NetworkRenderer(MathNet)
renderer.render('Visualization.html')