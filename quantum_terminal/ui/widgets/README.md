# Quantum Terminal UI Widgets

Reusable PyQt6 widget components for the Quantum Investment Terminal.

## Quick Start

```python
from quantum_terminal.ui.widgets import MetricCard, ChartWidget, DataTable

# Create a KPI card
metric = MetricCard(title="Sharpe Ratio", unit="pts")
metric.set_value(1.85)
metric.set_change(0.15)  # +0.15%
metric.show()

# Create a table
table = DataTable(columns=["Ticker", "Price", "Change %"])
table.set_data([
    {"Ticker": "AAPL", "Price": 150.50, "Change %": 2.5},
])
table.show()
```

## Widgets Overview

### 1. MetricCard
KPI display with value, change %, and color-coded indicator.

```python
card = MetricCard(title="VaR", unit="$")
card.set_value(250000)
card.set_change(-5.2)  # Red (negative)
card.set_warning_level("warning")  # Orange border
```

**Signals**: `value_clicked(str)`

---

### 2. ChartWidget
Interactive candlestick chart with technical indicators.

```python
chart = ChartWidget(title="AAPL Daily")
chart.plot_candlestick(ohlcv_dataframe)
chart.add_moving_average(period=20, ma_type="SMA")
chart.add_bollinger_bands(period=20, std_dev=2)
```

---

### 3. DataTable
Sortable, filterable table with color-coded values.

```python
table = DataTable(columns=["Ticker", "Price", "Change %"])
table.set_data(list_of_dicts)  # or set_dataframe(pd.DataFrame)
table.sort_by_column(1, ascending=False)  # Sort by Price

# Get selected row
row = table.get_selected_row()  # Returns dict
```

**Signals**: `row_selected(int)`, `cell_double_clicked(int, int)`

---

### 4. TickerSearch
Autocomplete ticker search with fuzzy matching.

```python
search = TickerSearch(tickers=["AAPL", "MSFT", "GOOGL"])
search.ticker_selected.connect(on_ticker_selected)

# Fuzzy match: "ap" -> ["AAPL"]
# Case-insensitive: "msft" -> ["MSFT"]
```

**Signals**: `ticker_selected(str)`, `search_text_changed(str)`

---

### 5. AlertBanner
Notification banner with auto-dismiss.

```python
banner = AlertBanner()

# Info banner (5 seconds)
banner.show_alert("Processing...", level="info", duration_ms=5000)

# Error banner (no auto-dismiss)
banner.show_alert("Connection failed!", level="error", duration_ms=0)

# Success (2 seconds)
banner.show_alert("Trade executed!", level="success", duration_ms=2000)
```

**Types**: `info` (blue), `warning` (orange), `error` (red), `success` (green)

**Signals**: `dismissed()`

---

### 6. AIChatWidget
Multi-turn chat interface with message history.

```python
chat = AIChatWidget()

# Add messages
chat.add_message("user", "What's the PE ratio?")
chat.add_message("assistant", "Your portfolio PE is 18.5")

# Show typing indicator during AI response
chat.add_typing_indicator()
# ... wait for response ...
chat.remove_typing_indicator()
chat.add_message("assistant", "Response here")

# Export history
history = chat.get_history()  # List of (role, text, timestamp)
```

**Signals**: `message_sent(str)`

---

### 7. HeatmapWidget
Interactive sector/market heatmap visualization.

```python
heatmap = HeatmapWidget(title="Sector Performance")

# Treemap
heatmap.plot_heatmap(
    labels=["AAPL", "MSFT", "GOOGL"],
    values=[5.2, 3.1, -1.5]
)

# Sector heatmap
heatmap.plot_sector_heatmap({
    "Technology": 5.2,
    "Healthcare": 1.8,
    "Energy": 3.1,
})

# Correlation matrix
heatmap.plot_correlation_heatmap(correlation_df)
```

---

### 8. EquityCurveWidget
Portfolio equity curve with drawdown band.

```python
equity = EquityCurveWidget(title="Portfolio Equity")

# Plot equity + drawdown
equity.plot_both([100000, 102000, 101500, 103200, ...])

# Get statistics
stats = equity.get_statistics(equity_list)
# Returns: {
#   "total_return": 15.5,
#   "sharpe_ratio": 1.2,
#   "max_drawdown": -8.3,
#   "win_rate": 65.2,
#   "volatility": 12.1,
# }

# Add metrics overlay
equity.add_performance_metrics(stats)
```

---

## Common Patterns

### Connect Signals
```python
def on_ticker_selected(ticker):
    print(f"Selected: {ticker}")

search.ticker_selected.connect(on_ticker_selected)
```

### Handle Table Selection
```python
def on_row_selected(row_idx):
    row = table.get_selected_row()
    print(f"Row {row_idx}: {row}")

table.row_selected.connect(on_row_selected)
```

### Styling
All widgets use QSS stylesheets. Override default:
```python
widget.setStyleSheet("""
    QWidget {
        background-color: #2A2A2A;
        color: #FFFFFF;
    }
""")
```

### Dark Theme (Default)
- Background: `#1E1E1E` (very dark gray)
- Accent (positive): `#00D26A` (green)
- Accent (negative): `#FF3B30` (red)
- Text: `#FFFFFF` (white)
- Secondary text: `#A0A0A0` (light gray)

---

## Performance Tips

1. **DataTable**: Use `set_data()` once, then `add_row()` for incremental updates
2. **ChartWidget**: Clear old data with `clear()` before plotting new
3. **HeatmapWidget**: Uses QWebEngine - heavy, cache results when possible
4. **AIChatWidget**: Limit history to 100 messages for smooth scrolling

---

## Integration with Application Layer

Each widget is independent but designed to integrate with use cases:

```python
# application/market/use_cases.py
class GetQuote:
    def execute(self, ticker: str):
        data = self.market_provider.get_quote(ticker)
        return data

# ui/panels/market_panel.py
class MarketPanel(QWidget):
    def __init__(self, get_quote: GetQuote):
        self.search = TickerSearch(tickers=available_tickers)
        self.search.ticker_selected.connect(self._on_ticker_selected)
        self.chart = ChartWidget()
        self.get_quote = get_quote
    
    def _on_ticker_selected(self, ticker: str):
        quote = self.get_quote.execute(ticker)
        self.chart.plot_candlestick(quote.ohlcv)
```

---

## Testing

Run widget tests:
```bash
pytest tests/test_metric_card.py -v
pytest tests/test_data_table.py -v
pytest tests/test_chart_widget.py -v
pytest tests/test_ticker_search.py -v
```

---

## Requirements

- `PyQt6` - UI framework
- `pyqtgraph` - Charting (ChartWidget, EquityCurveWidget)
- `plotly` - Web-based charts (HeatmapWidget)
- `pandas` - Data handling
- `numpy` - Numerical computing

---

## License

Proprietary - Quantum Investment Terminal
