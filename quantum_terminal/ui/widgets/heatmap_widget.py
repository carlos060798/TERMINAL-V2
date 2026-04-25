"""
HeatmapWidget: Sector/market heatmap visualization using Plotly and QWebEngine.

Features: Interactive treemap, real-time updates, sector allocation view.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Optional
import json


class HeatmapWidget(QWidget):
    """Interactive sector/market heatmap using Plotly."""

    def __init__(self, title: str = "Market Heatmap"):
        """
        Initialize HeatmapWidget.

        Args:
            title: Heatmap title
        """
        super().__init__()
        self.title = title
        self.data: Optional[pd.DataFrame] = None

        self.initUI()

    def initUI(self) -> None:
        """Build heatmap UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # QWebEngineView for Plotly
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet(
            """
            QWebEngineView {
                background-color: #1E1E1E;
                border: 1px solid #2A2A2A;
                border-radius: 4px;
            }
        """
        )
        layout.addWidget(self.web_view)
        self.setLayout(layout)

    def plot_heatmap(
        self, labels: List[str], values: List[float], parents: Optional[List[str]] = None
    ) -> None:
        """
        Plot treemap heatmap.

        Args:
            labels: Sector/ticker labels
            values: Performance or allocation values
            parents: Parent categories for hierarchical treemap
        """
        if not labels or not values:
            return

        # Create treemap
        if parents:
            fig = go.Figure(
                go.Treemap(
                    labels=labels,
                    values=values,
                    parents=parents,
                    marker=dict(
                        colorscale="RdYlGn",
                        cmid=0,
                        line=dict(width=1, color="#2A2A2A"),
                        colorbar=dict(title="Performance %"),
                    ),
                    text=labels,
                    textposition="middle center",
                    textfont=dict(size=12, color="#FFFFFF"),
                )
            )
        else:
            # Flat treemap
            fig = go.Figure(
                go.Treemap(
                    labels=labels,
                    values=values,
                    marker=dict(
                        colorscale="RdYlGn",
                        cmid=0,
                        line=dict(width=1, color="#2A2A2A"),
                        colorbar=dict(title="Change %"),
                    ),
                    text=labels,
                    textposition="middle center",
                    textfont=dict(size=12, color="#FFFFFF"),
                )
            )

        fig.update_layout(
            title=dict(text=self.title, font=dict(size=16, color="#FFFFFF")),
            paper_bgcolor="#1E1E1E",
            plot_bgcolor="#1E1E1E",
            font=dict(family="Inter, sans-serif", color="#A0A0A0"),
            margin=dict(t=40, l=0, r=0, b=0),
            hovermode="closest",
        )

        # Render to HTML and display
        html_content = fig.to_html(include_plotlyjs="cdn", div_id="heatmap")
        self.web_view.setHtml(html_content)

    def plot_sector_heatmap(self, sector_data: Dict[str, float]) -> None:
        """
        Plot sector allocation heatmap.

        Args:
            sector_data: Dict of sector -> change_percentage
        """
        sectors = list(sector_data.keys())
        values = list(sector_data.values())
        self.plot_heatmap(sectors, values)

    def plot_stock_grid(
        self, tickers: List[str], performances: List[float]
    ) -> None:
        """
        Plot stock performance grid.

        Args:
            tickers: List of ticker symbols
            performances: List of performance percentages
        """
        # Color by performance
        colors = ["#00D26A" if p > 0 else "#FF3B30" for p in performances]
        text_values = [f"{p:+.2f}%" for p in performances]

        fig = go.Figure(
            data=go.Heatmap(
                z=performances,
                x=tickers,
                text=text_values,
                texttemplate="%{text}",
                colorscale="RdYlGn",
                zmid=0,
                colorbar=dict(title="Return %"),
                hovertemplate="<b>%{x}</b><br>Return: %{z:.2f}%<extra></extra>",
            )
        )

        fig.update_layout(
            title=dict(text=self.title, font=dict(size=16, color="#FFFFFF")),
            paper_bgcolor="#1E1E1E",
            plot_bgcolor="#1E1E1E",
            font=dict(family="Inter, sans-serif", color="#A0A0A0"),
            xaxis=dict(side="bottom"),
            yaxis=dict(tickmode="linear", tick0=0),
            margin=dict(t=40, l=40, r=40, b=40),
            height=300,
        )

        html_content = fig.to_html(include_plotlyjs="cdn", div_id="stock_grid")
        self.web_view.setHtml(html_content)

    def plot_correlation_heatmap(self, correlation_matrix: pd.DataFrame) -> None:
        """
        Plot correlation matrix heatmap.

        Args:
            correlation_matrix: Symmetric correlation matrix
        """
        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale="RdYlGn",
                zmid=0.5,
                zmin=0,
                zmax=1,
                text=correlation_matrix.values.round(2),
                texttemplate="%{text}",
                colorbar=dict(title="Correlation"),
                hovertemplate="<b>%{x} vs %{y}</b><br>Correlation: %{z:.3f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=dict(text="Correlation Matrix", font=dict(size=16, color="#FFFFFF")),
            paper_bgcolor="#1E1E1E",
            plot_bgcolor="#1E1E1E",
            font=dict(family="Inter, sans-serif", color="#A0A0A0"),
            margin=dict(t=40, l=100, r=40, b=100),
            height=500,
        )

        html_content = fig.to_html(include_plotlyjs="cdn", div_id="correlation")
        self.web_view.setHtml(html_content)

    def update_data(self, new_data: Dict[str, float]) -> None:
        """
        Update heatmap data.

        Args:
            new_data: New data dict (labels -> values)
        """
        self.plot_heatmap(list(new_data.keys()), list(new_data.values()))

    def clear(self) -> None:
        """Clear heatmap."""
        self.web_view.setHtml("")

    def export_html(self, filepath: str) -> None:
        """
        Export heatmap to HTML file.

        Args:
            filepath: Path to save HTML
        """
        html_content = self.web_view.page().toHtml(lambda html: None)
        # Note: Plotly figures should be saved before export is needed
