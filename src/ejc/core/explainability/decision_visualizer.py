"""
Decision Path Visualization for EJE

Visual representation of decision flow through multi-critic pipeline.
Shows critic evaluations, conflicts, consensus, and aggregation logic.

Implements Issue #169: Create Decision Path Visualization

References:
- D3.js for interactive visualizations
- Graphviz for graph layouts
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class VisualizationType(Enum):
    """Types of decision visualizations."""
    TREE = "tree"                  # Hierarchical tree view
    FLOW = "flow"                  # Flow diagram
    TIMELINE = "timeline"          # Temporal sequence
    NETWORK = "network"            # Network graph
    SANKEY = "sankey"             # Sankey diagram


class ExportFormat(Enum):
    """Export formats for visualizations."""
    SVG = "svg"
    PNG = "png"
    HTML = "html"
    JSON = "json"


@dataclass
class VisualizationNode:
    """A node in the decision visualization."""
    id: str
    type: str  # 'input', 'critic', 'aggregator', 'governance', 'output'
    label: str
    data: Dict[str, Any] = field(default_factory=dict)
    style: Dict[str, str] = field(default_factory=dict)


@dataclass
class VisualizationEdge:
    """An edge connecting nodes in the visualization."""
    source: str
    target: str
    label: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    style: Dict[str, str] = field(default_factory=dict)


class DecisionVisualizer:
    """
    Creates visual representations of EJE decision flows.

    Generates multiple visualization types showing:
    - Critic evaluations and confidence levels
    - Weighted voting and consensus
    - Conflicts and disagreements
    - Aggregation and governance logic
    - Final decision path
    """

    def __init__(self):
        """Initialize decision visualizer."""
        self.nodes: List[VisualizationNode] = []
        self.edges: List[VisualizationEdge] = []

    def visualize_decision(
        self,
        decision: Dict[str, Any],
        visualization_type: VisualizationType = VisualizationType.FLOW,
        highlight_conflicts: bool = True,
        show_weights: bool = True
    ) -> Dict[str, Any]:
        """
        Generate visualization for an EJE decision.

        Args:
            decision: EJE Decision object (as dict)
            visualization_type: Type of visualization to generate
            highlight_conflicts: Highlight conflicting critics
            show_weights: Display critic weights

        Returns:
            Visualization data structure ready for rendering
        """
        # Reset state
        self.nodes = []
        self.edges = []

        # Build visualization based on type
        if visualization_type == VisualizationType.TREE:
            vis_data = self._build_tree_visualization(decision, highlight_conflicts, show_weights)
        elif visualization_type == VisualizationType.FLOW:
            vis_data = self._build_flow_visualization(decision, highlight_conflicts, show_weights)
        elif visualization_type == VisualizationType.TIMELINE:
            vis_data = self._build_timeline_visualization(decision)
        elif visualization_type == VisualizationType.NETWORK:
            vis_data = self._build_network_visualization(decision, highlight_conflicts)
        elif visualization_type == VisualizationType.SANKEY:
            vis_data = self._build_sankey_visualization(decision)
        else:
            vis_data = self._build_flow_visualization(decision, highlight_conflicts, show_weights)

        return {
            'decision_id': decision.get('decision_id', 'unknown'),
            'visualization_type': visualization_type.value,
            'data': vis_data,
            'metadata': self._extract_metadata(decision)
        }

    def _build_flow_visualization(
        self,
        decision: Dict[str, Any],
        highlight_conflicts: bool,
        show_weights: bool
    ) -> Dict[str, Any]:
        """Build flow diagram visualization."""
        # Input node
        input_node = VisualizationNode(
            id='input',
            type='input',
            label='Input Data',
            data=decision.get('input_data', {}),
            style={'shape': 'box', 'color': '#4A90E2'}
        )
        self.nodes.append(input_node)

        # Critic nodes
        critic_reports = decision.get('critic_reports', [])
        final_verdict = self._get_final_verdict(decision)

        for i, report in enumerate(critic_reports):
            critic_name = report.get('critic_name', f'Critic{i}')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.5)

            # Determine if this critic conflicts with final verdict
            is_conflict = verdict != final_verdict if highlight_conflicts else False

            # Style based on verdict and conflict
            color = self._get_verdict_color(verdict, is_conflict)

            critic_node = VisualizationNode(
                id=f'critic_{i}',
                type='critic',
                label=f'{critic_name}\\n{verdict} ({confidence:.2f})',
                data={
                    'critic_name': critic_name,
                    'verdict': verdict,
                    'confidence': confidence,
                    'justification': report.get('justification', ''),
                    'is_conflict': is_conflict
                },
                style={'shape': 'ellipse', 'color': color}
            )
            self.nodes.append(critic_node)

            # Edge from input to critic
            self.edges.append(VisualizationEdge(
                source='input',
                target=f'critic_{i}',
                label=None,
                style={'arrow': 'forward'}
            ))

        # Aggregator node
        aggregation = decision.get('aggregation', {})
        agg_verdict = aggregation.get('verdict', 'UNKNOWN')
        agg_confidence = aggregation.get('confidence', 0.5)

        aggregator_node = VisualizationNode(
            id='aggregator',
            type='aggregator',
            label=f'Aggregator\\n{agg_verdict} ({agg_confidence:.2f})',
            data=aggregation,
            style={'shape': 'hexagon', 'color': '#F5A623'}
        )
        self.nodes.append(aggregator_node)

        # Edges from critics to aggregator
        for i in range(len(critic_reports)):
            edge_label = None
            if show_weights:
                # Could add weight information here if available
                pass

            self.edges.append(VisualizationEdge(
                source=f'critic_{i}',
                target='aggregator',
                label=edge_label,
                style={'arrow': 'forward'}
            ))

        # Governance node (if applied)
        governance = decision.get('governance_outcome', {})
        if governance and governance.get('governance_applied', False):
            gov_verdict = governance.get('verdict', agg_verdict)
            gov_confidence = governance.get('confidence', agg_confidence)

            governance_node = VisualizationNode(
                id='governance',
                type='governance',
                label=f'Governance\\n{gov_verdict} ({gov_confidence:.2f})',
                data=governance,
                style={'shape': 'diamond', 'color': '#BD10E0'}
            )
            self.nodes.append(governance_node)

            self.edges.append(VisualizationEdge(
                source='aggregator',
                target='governance',
                label='Governance Rules',
                style={'arrow': 'forward', 'dash': 'dashed'}
            ))

            final_source = 'governance'
        else:
            final_source = 'aggregator'

        # Output node
        output_node = VisualizationNode(
            id='output',
            type='output',
            label=f'Final Decision\\n{final_verdict}',
            data={'verdict': final_verdict},
            style={'shape': 'box', 'color': self._get_verdict_color(final_verdict, False)}
        )
        self.nodes.append(output_node)

        self.edges.append(VisualizationEdge(
            source=final_source,
            target='output',
            style={'arrow': 'forward', 'weight': 'bold'}
        ))

        return {
            'nodes': [self._node_to_dict(n) for n in self.nodes],
            'edges': [self._edge_to_dict(e) for e in self.edges],
            'layout': 'hierarchical'
        }

    def _build_tree_visualization(
        self,
        decision: Dict[str, Any],
        highlight_conflicts: bool,
        show_weights: bool
    ) -> Dict[str, Any]:
        """Build tree visualization (hierarchical)."""
        # Similar to flow but with strict hierarchy
        # Root -> Critics -> Aggregator -> Governance -> Final
        tree_data = {
            'name': 'Decision',
            'children': []
        }

        # Input level
        input_child = {
            'name': 'Input',
            'data': decision.get('input_data', {}),
            'children': []
        }

        # Critics level
        final_verdict = self._get_final_verdict(decision)
        for report in decision.get('critic_reports', []):
            critic_name = report.get('critic_name', 'Unknown')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.5)
            is_conflict = verdict != final_verdict if highlight_conflicts else False

            critic_child = {
                'name': f'{critic_name}: {verdict} ({confidence:.2f})',
                'verdict': verdict,
                'confidence': confidence,
                'is_conflict': is_conflict,
                'color': self._get_verdict_color(verdict, is_conflict)
            }
            input_child['children'].append(critic_child)

        tree_data['children'].append(input_child)

        # Aggregation level
        aggregation = decision.get('aggregation', {})
        agg_child = {
            'name': f"Aggregation: {aggregation.get('verdict', 'UNKNOWN')}",
            'data': aggregation,
            'children': []
        }

        # Governance level (if applied)
        governance = decision.get('governance_outcome', {})
        if governance and governance.get('governance_applied', False):
            gov_child = {
                'name': f"Governance: {governance.get('verdict', 'UNKNOWN')}",
                'data': governance
            }
            agg_child['children'].append(gov_child)

        tree_data['children'].append(agg_child)

        return tree_data

    def _build_timeline_visualization(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Build timeline visualization showing temporal sequence."""
        timeline = []

        # Event 1: Input received
        timeline.append({
            'time': 0,
            'label': 'Input Received',
            'type': 'input',
            'data': decision.get('input_data', {})
        })

        # Event 2: Critics execute
        critic_reports = decision.get('critic_reports', [])
        for i, report in enumerate(critic_reports):
            timeline.append({
                'time': i + 1,
                'label': f"{report.get('critic_name', 'Critic')} evaluates",
                'type': 'critic',
                'verdict': report.get('verdict'),
                'confidence': report.get('confidence')
            })

        # Event 3: Aggregation
        timeline.append({
            'time': len(critic_reports) + 1,
            'label': 'Aggregation',
            'type': 'aggregator',
            'verdict': decision.get('aggregation', {}).get('verdict')
        })

        # Event 4: Governance (if applied)
        governance = decision.get('governance_outcome', {})
        if governance and governance.get('governance_applied', False):
            timeline.append({
                'time': len(critic_reports) + 2,
                'label': 'Governance Applied',
                'type': 'governance',
                'verdict': governance.get('verdict')
            })

        # Event 5: Final decision
        timeline.append({
            'time': len(timeline),
            'label': 'Final Decision',
            'type': 'output',
            'verdict': self._get_final_verdict(decision)
        })

        return {'timeline': timeline}

    def _build_network_visualization(
        self,
        decision: Dict[str, Any],
        highlight_conflicts: bool
    ) -> Dict[str, Any]:
        """Build network graph showing critic relationships."""
        # Similar to flow but emphasizes connections between critics
        # that agree/disagree

        nodes = []
        edges = []

        # Add critic nodes
        critic_reports = decision.get('critic_reports', [])
        final_verdict = self._get_final_verdict(decision)

        for i, report in enumerate(critic_reports):
            critic_name = report.get('critic_name', f'Critic{i}')
            verdict = report.get('verdict', 'UNKNOWN')
            is_conflict = verdict != final_verdict if highlight_conflicts else False

            nodes.append({
                'id': f'critic_{i}',
                'label': critic_name,
                'verdict': verdict,
                'confidence': report.get('confidence', 0.5),
                'is_conflict': is_conflict,
                'color': self._get_verdict_color(verdict, is_conflict)
            })

        # Add edges between critics with same verdict (consensus)
        for i in range(len(critic_reports)):
            for j in range(i + 1, len(critic_reports)):
                if critic_reports[i].get('verdict') == critic_reports[j].get('verdict'):
                    edges.append({
                        'source': f'critic_{i}',
                        'target': f'critic_{j}',
                        'type': 'consensus',
                        'style': {'dash': 'solid', 'color': '#2ECC71'}
                    })

        return {
            'nodes': nodes,
            'edges': edges,
            'layout': 'force-directed'
        }

    def _build_sankey_visualization(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Build Sankey diagram showing vote flow."""
        nodes = []
        links = []

        # Source nodes: each unique verdict type among critics
        verdict_counts = {}
        critic_reports = decision.get('critic_reports', [])

        for report in critic_reports:
            verdict = report.get('verdict', 'UNKNOWN')
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Add verdict nodes
        node_index = {}
        for i, verdict in enumerate(verdict_counts.keys()):
            node_index[verdict] = i
            nodes.append({
                'name': f'{verdict} ({verdict_counts[verdict]})',
                'color': self._get_verdict_color(verdict, False)
            })

        # Add aggregation node
        agg_index = len(nodes)
        aggregation = decision.get('aggregation', {})
        nodes.append({
            'name': f"Aggregated: {aggregation.get('verdict', 'UNKNOWN')}",
            'color': '#F5A623'
        })

        # Add final decision node
        final_index = len(nodes)
        final_verdict = self._get_final_verdict(decision)
        nodes.append({
            'name': f"Final: {final_verdict}",
            'color': self._get_verdict_color(final_verdict, False)
        })

        # Links from verdicts to aggregation
        for verdict, count in verdict_counts.items():
            links.append({
                'source': node_index[verdict],
                'target': agg_index,
                'value': count,
                'color': self._get_verdict_color(verdict, False, alpha=0.4)
            })

        # Link from aggregation to final
        links.append({
            'source': agg_index,
            'target': final_index,
            'value': len(critic_reports),
            'color': '#F5A623'
        })

        return {
            'nodes': nodes,
            'links': links,
            'layout': 'sankey'
        }

    def export(
        self,
        visualization_data: Dict[str, Any],
        format: ExportFormat = ExportFormat.JSON
    ) -> str:
        """
        Export visualization in specified format.

        Args:
            visualization_data: Visualization data structure
            format: Export format (SVG, PNG, HTML, JSON)

        Returns:
            Exported visualization as string
        """
        if format == ExportFormat.JSON:
            return self._export_json(visualization_data)
        elif format == ExportFormat.HTML:
            return self._export_html(visualization_data)
        elif format == ExportFormat.SVG:
            return self._export_svg(visualization_data)
        elif format == ExportFormat.PNG:
            return self._export_png(visualization_data)
        else:
            return self._export_json(visualization_data)

    def _export_json(self, visualization_data: Dict[str, Any]) -> str:
        """Export as JSON."""
        return json.dumps(visualization_data, indent=2)

    def _export_html(self, visualization_data: Dict[str, Any]) -> str:
        """Export as interactive HTML."""
        vis_type = visualization_data.get('visualization_type', 'flow')

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>EJE Decision Visualization</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
        }}
        .metadata {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        #visualization {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px;
            min-height: 400px;
        }}
        .node {{
            padding: 10px;
            margin: 5px;
            border-radius: 4px;
            display: inline-block;
        }}
        .conflict {{
            border: 2px solid #E74C3C;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>EJE Decision Visualization</h1>
        <div class="metadata">
            <strong>Decision ID:</strong> {visualization_data.get('decision_id', 'N/A')}<br>
            <strong>Visualization Type:</strong> {vis_type}<br>
            <strong>Final Verdict:</strong> {visualization_data.get('metadata', {}).get('final_verdict', 'N/A')}
        </div>
        <div id="visualization">
            <pre>{json.dumps(visualization_data.get('data', {}), indent=2)}</pre>
        </div>
    </div>
    <script>
        // Visualization data
        const vizData = {json.dumps(visualization_data)};
        console.log('Visualization data:', vizData);

        // TODO: Integrate with D3.js or other visualization library
        // for interactive rendering
    </script>
</body>
</html>
"""
        return html_template

    def _export_svg(self, visualization_data: Dict[str, Any]) -> str:
        """Export as SVG (simplified version)."""
        # Basic SVG generation
        # For production, would use proper graph layout library
        svg_parts = ['<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">']

        data = visualization_data.get('data', {})
        nodes = data.get('nodes', [])

        # Simple layout: vertical stack
        y_offset = 50
        for node in nodes:
            x = 400  # Center
            svg_parts.append(f'<circle cx="{x}" cy="{y_offset}" r="30" fill="{node.get("style", {}).get("color", "#ccc")}" />')
            svg_parts.append(f'<text x="{x}" y="{y_offset}" text-anchor="middle" dy=".3em">{node.get("label", "")[:20]}</text>')
            y_offset += 100

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _export_png(self, visualization_data: Dict[str, Any]) -> str:
        """Export as PNG (requires external rendering)."""
        # Would typically use:
        # - Graphviz for graph rendering
        # - Matplotlib for plots
        # - Selenium/Puppeteer for HTML->PNG

        return "PNG export requires additional rendering libraries (Graphviz, Matplotlib, or headless browser)"

    def _get_final_verdict(self, decision: Dict[str, Any]) -> str:
        """Extract final verdict from decision."""
        governance = decision.get('governance_outcome', {})
        if governance and 'verdict' in governance:
            return governance['verdict']

        aggregation = decision.get('aggregation', {})
        if aggregation and 'verdict' in aggregation:
            return aggregation['verdict']

        return 'UNKNOWN'

    def _get_verdict_color(self, verdict: str, is_conflict: bool, alpha: float = 1.0) -> str:
        """Get color for verdict display."""
        color_map = {
            'APPROVE': '#2ECC71',  # Green
            'DENY': '#E74C3C',      # Red
            'REVIEW': '#F39C12',    # Orange
            'UNKNOWN': '#95A5A6'    # Gray
        }

        color = color_map.get(verdict, '#95A5A6')

        if is_conflict:
            # Darken for conflicts
            color = '#C0392B'  # Dark red for conflicts

        return color

    def _extract_metadata(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for visualization."""
        return {
            'final_verdict': self._get_final_verdict(decision),
            'num_critics': len(decision.get('critic_reports', [])),
            'confidence': decision.get('governance_outcome', {}).get('confidence',
                                    decision.get('aggregation', {}).get('confidence', 0.0)),
            'has_conflicts': self._detect_conflicts(decision),
            'consensus_ratio': self._calculate_consensus_ratio(decision)
        }

    def _detect_conflicts(self, decision: Dict[str, Any]) -> bool:
        """Detect if there are conflicting critic verdicts."""
        critic_reports = decision.get('critic_reports', [])
        if not critic_reports:
            return False

        verdicts = [r.get('verdict') for r in critic_reports]
        return len(set(verdicts)) > 1

    def _calculate_consensus_ratio(self, decision: Dict[str, Any]) -> float:
        """Calculate ratio of critics agreeing with final verdict."""
        critic_reports = decision.get('critic_reports', [])
        if not critic_reports:
            return 0.0

        final_verdict = self._get_final_verdict(decision)
        agreeing = sum(1 for r in critic_reports if r.get('verdict') == final_verdict)

        return agreeing / len(critic_reports)

    def _node_to_dict(self, node: VisualizationNode) -> Dict[str, Any]:
        """Convert VisualizationNode to dictionary."""
        return {
            'id': node.id,
            'type': node.type,
            'label': node.label,
            'data': node.data,
            'style': node.style
        }

    def _edge_to_dict(self, edge: VisualizationEdge) -> Dict[str, Any]:
        """Convert VisualizationEdge to dictionary."""
        return {
            'source': edge.source,
            'target': edge.target,
            'label': edge.label,
            'data': edge.data,
            'style': edge.style
        }


# Export
__all__ = ['DecisionVisualizer', 'VisualizationType', 'ExportFormat']
