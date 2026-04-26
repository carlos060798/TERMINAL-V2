# Risk Manager Panel - Integration Guide

## Quick Start

### 1. Import the Panel
```python
from quantum_terminal.ui.panels.risk_panel import RiskManagerPanel
```

### 2. Create Instance
```python
risk_panel = RiskManagerPanel()
```

### 3. Add to Main Window
```python
# In your main window's __init__:
self.tabs.addTab(risk_panel, "Risk Manager")
```

### 4. Connect Signals
```python
# Handle risk limit changes
risk_panel.risk_limit_changed.connect(self.on_risk_limits_modified)

# Handle stress test results
risk_panel.stress_test_updated.connect(self.on_stress_test_completed)

# Handle correlation warnings
risk_panel.correlation_warning.connect(self.on_correlation_alert)
```

### 5. Feed Portfolio Data
```python
# When portfolio updates
portfolio_data = {
    "open_trades": [
        {"ticker": "AAPL", "entry": 150.0, "stop": 145.0, "qty": 100, "status": "Open"},
        ...
    ],
    "positions": [
        {"ticker": "AAPL", "price": 160.0, "qty": 100, "sector": "Technology"},
        ...
    ],
    "historical_returns": {
        "AAPL": [0.01, -0.02, 0.03, ...],  # Daily returns
        ...
    },
    "total_capital": 50000.0,
    "current_capital": 45000.0
}

risk_panel.update_portfolio_data(portfolio_data)
```

---

## Data Format Specification

### Portfolio Dictionary Structure

```python
{
    # List of open trading positions with defined risk (R)
    "open_trades": [
        {
            "ticker": str,              # "AAPL"
            "entry": float,             # Entry price: 150.0
            "stop": float,              # Stop loss: 145.0
            "qty": float,               # Quantity: 100
            "status": str,              # "Open" | "Closed"
        },
        ...
    ],
    
    # Current holdings (end-of-period positions)
    "positions": [
        {
            "ticker": str,              # "AAPL"
            "price": float,             # Current price: 160.0
            "qty": float,               # Quantity: 100
            "sector": str,              # For concentration: "Technology"
            "beta": float,              # Optional: 1.2 (for stress tests)
        },
        ...
    ],
    
    # Historical daily/weekly returns for each security
    "historical_returns": {
        "AAPL": [
            0.01,      # Day 1: +1%
            -0.02,     # Day 2: -2%
            0.03,      # Day 3: +3%
            ...        # Minimum 20 observations required
        ],
        "MSFT": [...],
        ...
    },
    
    # Portfolio totals
    "total_capital": float,             # Initial: 50000.0
    "current_capital": float,           # Current: 45000.0
}
```

**Minimum Requirements**:
- At least 1 position
- At least 20 historical return observations (for VaR)
- Returns as decimals (0.01 for +1%)

---

## Signal Callbacks

### Signal 1: `risk_limit_changed`
**Emitted when**: User modifies risk limits and clicks "Save"

**Data**:
```python
{
    "max_drawdown_daily": float,       # 2.0 (%)
    "max_drawdown_total": float,       # 10.0 (%)
    "capital_at_risk_limit": float,    # 10000.0 ($)
    "max_position_size": float,        # 1000.0 ($)
}
```

**Handler Example**:
```python
def on_risk_limits_modified(self, limits_dict):
    # Save to database
    self.settings.save_risk_limits(limits_dict)
    
    # Check current exposure against new limits
    self.validate_current_positions(limits_dict)
```

---

### Signal 2: `stress_test_updated`
**Emitted when**: User clicks a stress test scenario button

**Data**:
```python
{
    "scenario": str,        # "-20%" | "-50%" | "-35%"
    "pnl": float,          # -5000.0 ($) - projected loss
    "pct": float,          # -24.5 (%) - portfolio impact
}
```

**Handler Example**:
```python
def on_stress_test_completed(self, results):
    scenario = results["scenario"]
    pnl = results["pnl"]
    
    # Log for journal
    print(f"Market {scenario} scenario: Portfolio loses ${abs(pnl):,.0f}")
    
    # Check if acceptable risk
    if abs(pnl) > self.max_acceptable_loss:
        self.show_risk_warning(results)
```

---

### Signal 3: `correlation_warning`
**Emitted when**: Correlation > 0.70 detected between holdings

**Data**:
```python
(
    ticker_pair: str,       # "AAPL-MSFT"
    correlation: float,     # 0.85
)
```

**Handler Example**:
```python
def on_correlation_alert(self, pair: str, corr: float):
    # Notify user
    alert = f"High correlation detected: {pair} (r={corr:.2f})\n"
    alert += "Consider diversifying away from one position."
    self.show_notification(alert)
    
    # Log event
    self.logger.warning(f"High correlation: {pair} = {corr:.2f}")
```

---

## Tab Reference

### Tab 1: Risk Exposure
```
Display: Capital at Risk | Risk Limit | % Used
Alert: Red if >80%, Yellow if >60%

Table: Ticker | Entry | Stop | Risk($) | % of Total | Status
```

**When to use**: Monitor daily trading risk

---

### Tab 2: VaR Analysis
```
Method: [Historical ▼] [Monte Carlo] [Parametric]

Results:
  95% VaR: -3.5% | $3,500
  99% VaR: -5.2% | $5,200

Interpretation: "99% of days, max loss is $5,200"
```

**When to use**: Understand portfolio downside risk, set position sizing

---

### Tab 3: Correlations
```
Heatmap: Color matrix (Red=concentrated, Green=diversified)

High Correlations:
  AAPL-MSFT: 0.85 ⚠️
  TSLA-GOOG: 0.78 ⚠️
```

**When to use**: Check portfolio diversification, identify concentrated risks

---

### Tab 4: Concentration
```
Sector Concentration:
  Technology: 60.5% ⚠️ HIGH
  Financials: 30.2%
  Healthcare: 9.3%

Position Concentration:
  AAPL: 25.1% ⚠️ HIGH
  MSFT: 22.3%
  JPM: 14.8%

Pie Chart: Visual allocation
```

**When to use**: Ensure diversification, identify over-weighted positions

---

### Tab 5: Efficient Frontier
```
Chart:
  Red line: All efficient portfolios
  Blue dot: Your current portfolio
  Green star: Optimal portfolio (max Sharpe)

Recommendation: "Consider rebalancing to reduce risk"
```

**When to use**: Optimize portfolio allocation, validate position sizing

---

### Tab 6: Stress Testing
```
Buttons: [Simulate -20%] [Simulate -50% GFC] [Simulate -35% COVID]

Results Table:
  Scenario | Market Impact | Portfolio P&L | % Change | Recovery Time
  -20%     | -20%          | -$4,500       | -24%     | 42 days
  -50%     | -50%          | -$11,250      | -60%     | 105 days
  -35%     | -35%          | -$7,875       | -42%     | 73 days
```

**When to use**: Validate risk tolerance, ensure position sizing matches max acceptable loss

---

### Tab 7: Risk Limits
```
Form:
  Max Drawdown (Daily): [2.0] %
  Max Drawdown (Total): [10.0] %
  Capital at Risk Limit: [10000.0] $
  Max per Position: [1000.0] $

Button: [Save Risk Limits]
```

**When to use**: Configure risk parameters, enforce trading rules

---

## Code Examples

### Example 1: Complete Integration
```python
from PyQt6.QtWidgets import QMainWindow
from quantum_terminal.ui.panels.risk_panel import RiskManagerPanel

class MyTradingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create panel
        self.risk_panel = RiskManagerPanel()
        
        # Connect signals
        self.risk_panel.risk_limit_changed.connect(self.on_limits_changed)
        self.risk_panel.stress_test_updated.connect(self.on_stress_test)
        self.risk_panel.correlation_warning.connect(self.on_correlation)
        
        # Add to UI
        self.tabs.addTab(self.risk_panel, "Risk Manager")
    
    def on_portfolio_update(self):
        """Called when portfolio changes."""
        portfolio = self.get_portfolio_data()
        self.risk_panel.update_portfolio_data(portfolio)
    
    def on_limits_changed(self, limits):
        """User modified risk limits."""
        print(f"New limits: {limits}")
        self.database.save_risk_limits(limits)
    
    def on_stress_test(self, results):
        """Stress test completed."""
        loss = results["pnl"]
        if loss > -self.max_acceptable_loss:
            print("✓ Portfolio risk is acceptable")
        else:
            self.show_risk_warning(loss)
```

---

### Example 2: Loading Data from Database
```python
def get_portfolio_data():
    """Load portfolio from database."""
    trades = db.query_open_trades()
    positions = db.query_positions()
    
    # Fetch historical returns from data provider
    returns = {}
    for pos in positions:
        ticker = pos["ticker"]
        returns[ticker] = data_provider.get_returns(
            ticker, 
            lookback_days=252  # 1 year
        )
    
    return {
        "open_trades": [
            {
                "ticker": t["ticker"],
                "entry": float(t["entry_price"]),
                "stop": float(t["stop_loss"]),
                "qty": int(t["quantity"]),
                "status": t["status"],
            }
            for t in trades
        ],
        "positions": [
            {
                "ticker": p["ticker"],
                "price": float(p["current_price"]),
                "qty": int(p["quantity"]),
                "sector": p["sector"],
                "beta": float(p.get("beta", 1.0)),
            }
            for p in positions
        ],
        "historical_returns": returns,
        "total_capital": float(portfolio["total_capital"]),
        "current_capital": float(portfolio["current_value"]),
    }
```

---

### Example 3: Periodic Updates
```python
def setup_periodic_updates(self):
    """Update risk panel every 1 minute."""
    self.update_timer = QTimer()
    self.update_timer.timeout.connect(self.on_portfolio_update)
    self.update_timer.start(60000)  # 60 seconds

def on_portfolio_update(self):
    """Called every 60 seconds."""
    portfolio = self.get_portfolio_data()
    self.risk_panel.update_portfolio_data(portfolio)
    
    # Check for alerts
    capital_at_risk = sum(
        abs(t["entry"] - t["stop"]) * t["qty"]
        for t in portfolio["open_trades"]
    )
    
    if capital_at_risk > self.risk_panel.risk_limits["capital_at_risk_limit"]:
        self.show_alert("⚠️ Capital at Risk exceeds limit!")
```

---

## Troubleshooting

### Issue: "VaR shows N/A"
**Cause**: Insufficient historical data (< 20 observations)  
**Solution**: Provide at least 20 days of return data

### Issue: "Efficient Frontier not showing"
**Cause**: Riskfolio-lib not installed or portfolio has < 2 positions  
**Solution**: 
```bash
pip install riskfolio-lib
```
Or add 2+ positions to portfolio

### Issue: "High correlation warnings not appearing"
**Cause**: Correlations between holdings < 0.70  
**Solution**: Portfolio is well-diversified (working as intended)

### Issue: "Stress test shows zero impact"
**Cause**: Positions don't have beta value  
**Solution**: Add `"beta"` field to positions:
```python
{"ticker": "AAPL", "price": 160, "qty": 100, "beta": 1.15}
```

---

## Performance Tips

1. **Limit historical returns**: 250 days is sufficient (1 year of trading days)
2. **Cache calculations**: Store VaR/correlations in database, refresh hourly
3. **Async updates**: Call `update_portfolio_data()` in background thread
4. **Conditional rendering**: Don't update heatmap if correlations haven't changed

---

## Next Steps

1. **Test with sample data** using provided test fixtures
2. **Run test suite**: `pytest tests/test_risk_panel.py -v`
3. **Integrate into main window** (see examples above)
4. **Connect to your database** for persistence
5. **Set up periodic updates** (every 1 min recommended)

---

**Ready to integrate!** ✓
