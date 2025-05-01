function initializeInteractiveNetwork(networkData) {
    const graphDiv = document.getElementById('graph');
    if (!graphDiv) {
        console.error('Error: Missing graph container (div#graph)');
        return;
    }

    window.networkData = networkData;
    window.currentEdges = [];
    window.currentNodes = new Map();
    window.edgeTraceIndices = new Set();

    Object.values(window.networkData.nodes).forEach(node => {
        node.nextNode = node.nextNode || [];
        node.prevNode = node.prevNode || [];
    });

    if (typeof Plotly !== 'undefined') {
        setupPlotlyClickHandler(graphDiv);
        setupCatalogMenuHandler();
    } else {
        console.error('Error: Plotly not loaded');
    }
}

// handle click
function setupPlotlyClickHandler() {
    document.getElementById('graph').on('plotly_click', function (data) {
        if (!data.points || data.points.length === 0) return;

        const point = data.points[0].data;

        if (point.mode !== 'markers') return;

        // Click node
        const nodeId = point.customdata[0];
        const nodeData = window.networkData.nodes[nodeId];
        const curveNumber = data.points[0].curveNumber

        // update edges
        updateEdges(nodeId);

        // update node
        updateNodes(curveNumber, nodeId, nodeData)
    });
}

//handle classfy
function setupCatalogMenuHandler() {
    const graphDiv = document.getElementById('graph');

    graphDiv.on('plotly_restyle', function (data) {
        const meta = data[0];
        if (meta["meta.catalog_action"] === 'highlight') {
            highlightCatalog(meta["meta.catalog_name"]);
        }
        else if (meta.reset_all) {
            resetAllHighlights();
        }
    });
}

function highlightCatalog(catalogName) {
    const graphDiv = document.getElementById('graph');
    const allTraces = graphDiv.data;
    const catalogNodeIds = [];
    const catalogTraceIndices = [];
    const allNeighborIds = new Set();

    allTraces.forEach((trace, index) => {
        if (trace.mode === 'markers' && trace.customdata) {
            const nodeId = trace.customdata[0];
            const nodeData = window.networkData.nodes[nodeId];
            if (nodeData.group === catalogName) {
                catalogNodeIds.push(nodeId);
                catalogTraceIndices.push(index);

                nodeData.nextNode.forEach(neighborId => allNeighborIds.add(neighborId));
                nodeData.prevNode.forEach(neighborId => allNeighborIds.add(neighborId));
            }
        }
    });

    const neighborTraceIndices = [];
    allTraces.forEach((trace, index) => {
        if (trace.mode === 'markers' && trace.customdata) {
            const nodeId = trace.customdata[0];
            if (allNeighborIds.has(nodeId) && !catalogNodeIds.includes(nodeId)) {
                neighborTraceIndices.push(index);
            }
        }
    });

    resetCurrentNodes();
    removeCurrentEdges();

    const highlightUpdates = {
        'marker.color': [],
        'marker.opacity': []
    };

    // edges
    catalogTraceIndices.forEach(traceIndex => {
        const nodeId = allTraces[traceIndex].customdata[0];
        const nodeData = window.networkData.nodes[nodeId];

        highlightUpdates['marker.color'].push(nodeData.activeColor);
        highlightUpdates['marker.opacity'].push(1.0);

        window.currentNodes.set(traceIndex, {
            color: nodeData.defaultColor,
            opacity: 0.5 // 默认透明度
        });
    });

    // nodes
    neighborTraceIndices.forEach(traceIndex => {
        const nodeId = allTraces[traceIndex].customdata[0];
        const nodeData = window.networkData.nodes[nodeId];

        highlightUpdates['marker.color'].push(nodeData.activeColor);
        highlightUpdates['marker.opacity'].push(1); // 半透明

        window.currentNodes.set(traceIndex, {
            color: nodeData.defaultColor,
            opacity: 0.5 // 默认透明度
        });
    });

    Plotly.restyle(graphDiv, highlightUpdates, [...catalogTraceIndices, ...neighborTraceIndices]);

    const allEdges = new Set();

    catalogNodeIds.forEach(nodeId => {
        const node = window.networkData.nodes[nodeId];
        if (!node) return;

        node.nextNode.forEach(dst => allEdges.add(JSON.stringify([nodeId, dst])));
        node.prevNode.forEach(src => allEdges.add(JSON.stringify([src, nodeId])));
    });

    window.currentEdges = Array.from(allEdges).map(edge => JSON.parse(edge));
    addCurrentEdges();
}

// 重置所有高亮
function resetAllHighlights() {
    resetCurrentNodes();
    removeCurrentEdges();
}

function updateNodes(curveNumber, nodeId, nodeData) {

    resetCurrentNodes()

    showCurrentNodes(curveNumber, nodeId, nodeData)
}

function resetCurrentNodes() {
    const graphDiv = document.getElementById('graph');
    if (!graphDiv) return;

    const updates = {
        'marker.color': [],
        'marker.opacity': [],
    };
    const indices = [];

    window.currentNodes.forEach((style, index) => {
        updates['marker.color'].push(style.color);
        updates['marker.opacity'].push(style.opacity);
        indices.push(index);
        // console.log(style.color)
    });

    Plotly.restyle(graphDiv, updates, indices);
    window.currentNodes.clear();
}

function showCurrentNodes(curveNumber, nodeId, nodeData) {
    const graphDiv = document.getElementById('graph');
    const highlightIndices = []
    const highlightUpdates = {
        'marker.color': [],
        'marker.opacity': [],
    };
    highlightIndices.push(curveNumber);
    highlightUpdates['marker.color'].push(nodeData.activeColor);
    highlightUpdates['marker.opacity'].push(1.0);
    window.currentNodes.set(curveNumber, {
        color: nodeData.defaultColor,
        opacity: 0.5
    });

    const addNeighbors = (nodeIds) => {
        nodeIds.forEach(id => {
            const neighbor = window.networkData.nodes[id];
            if (neighbor) {
                const neighborTrace = graphDiv.data.findIndex(
                    t => t.customdata?.[0] === id
                );
                if (neighborTrace !== -1) {
                    highlightUpdates['marker.color'].push(neighbor.activeColor);
                    highlightUpdates['marker.opacity'].push(1);
                    highlightIndices.push(neighborTrace);
                    window.currentNodes.set(neighborTrace, {
                        color: neighbor.defaultColor,
                        opacity: 0.5
                    });
                }
            }
        });
    };

    addNeighbors(nodeData.nextNode);
    addNeighbors(nodeData.prevNode);

    Plotly.restyle(graphDiv, highlightUpdates, [
        curveNumber,
        ...Array.from({ length: highlightUpdates['marker.color'].length - 1 }, (_, i) => i)
    ]);
    Plotly.restyle(graphDiv, highlightUpdates, highlightIndices);
}

function updateEdges(nodeId) {
    const node = window.networkData.nodes[nodeId];
    if (!node) return;

    removeCurrentEdges();

    window.currentEdges = [
        ...node.nextNode.map(dst => [nodeId, dst]),
        ...node.prevNode.map(src => [src, nodeId])
    ];

    addCurrentEdges();
}

function removeCurrentEdges() {
    const graphDiv = document.getElementById('graph');
    if (!graphDiv || window.edgeTraceIndices.size === 0) return;

    const update = {
        'visible': Array.from(window.edgeTraceIndices).map(() => false)
    };

    Plotly.restyle(graphDiv, update, Array.from(window.edgeTraceIndices));
    window.edgeTraceIndices.clear();
}

function addCurrentEdges() {
    const graphDiv = document.getElementById('graph');
    if (!graphDiv || window.currentEdges.length === 0) return;

    const newEdgeTraces = window.currentEdges.map(([src, dst]) => {
        const srcNode = window.networkData.nodes[src];
        const dstNode = window.networkData.nodes[dst];
        const [pathX, pathY] = sigmoidCurve(srcNode.position, dstNode.position);

        return {
            x: pathX,
            y: pathY,
            mode: 'lines',
            line: { width: 1.5, color: srcNode.activeColor },
            hoverinfo: 'none',
            showlegend: false,
            visible: true,
            opacity: 0.5
        };
    });

    Plotly.addTraces(graphDiv, newEdgeTraces).then(() => {
        const traces = graphDiv.data;
        newEdgeTraces.forEach((_, i) => {
            window.edgeTraceIndices.add(traces.length - newEdgeTraces.length + i);
        });
    });
}

function sigmoidCurve(p0, p1, steepness = 5, num_points = 40) {
    const [x0, y0] = p0;
    const [x1, y1] = p1;

    const t = Array.from({ length: num_points }, (_, i) => i / (num_points - 1));
    const x = t.map(t_val => x0 + t_val * (x1 - x0));
    const y = t.map(t_val => {
        const sigmoid = 1 / (1 + Math.exp(-steepness * (2 * t_val - 1)));
        return y0 + (y1 - y0) * sigmoid;
    });

    return [x, y];
}