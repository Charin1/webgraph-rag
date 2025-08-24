// frontend/src/components/GraphViewer.jsx

import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import axios from 'axios';

export default function GraphViewer() {
  const ref = useRef(null);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });

  useEffect(() => {
    // Fetch graph data from the backend
    axios.get('/graph/get_full_graph?limit=150')
      .then(response => {
        const nodes = response.data.nodes.map(n => ({ data: { id: String(n.id), label: n.label, group: n.group } }));
        const edges = response.data.edges.map(e => ({ data: { source: String(e.source), target: String(e.target), label: e.label } }));
        setGraphData({ nodes, edges });
      })
      .catch(error => console.error("Failed to fetch graph data:", error));
  }, []);

  useEffect(() => {
    if (ref.current && graphData.nodes.length > 0) {
      const cy = cytoscape({
        container: ref.current,
        elements: [...graphData.nodes, ...graphData.edges],
        style: [
          { selector: 'node', style: { 'label': 'data(label)', 'font-size': '10px', 'width': '20px', 'height': '20px' } },
          { selector: 'node[group="WebPage"]', style: { 'background-color': '#0074D9' } },
          { selector: 'node[group="Entity"]', style: { 'background-color': '#FF4136', 'shape': 'round-rectangle' } },
          { selector: 'edge', style: { 'width': 1, 'line-color': '#ccc', 'target-arrow-color': '#ccc', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } }
        ],
        layout: { name: 'cose', animate: true, padding: 50 }
      });
      return () => cy.destroy();
    }
  }, [graphData]);

  return <div ref={ref} style={{ width: '100%', height: '100vh', background: '#fefefe' }} />;
}