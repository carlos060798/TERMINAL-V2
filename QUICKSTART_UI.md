# Quick Start - Quantum Terminal UI

## Launch the Application

```bash
# From project root
python main.py
```

## What You'll See

A Bloomberg-style investment terminal with:

```
┌─────────────────────────────────────────────────────┐
│  Market Ticker: S&P 500 | NASDAQ | BTC | WTI | ... │
├─────────────────────────────────────────────────────┤
│ File | Edit | View | Data | Help                    │
├──────────┬──────────────────────┬──────────────────┤
│          │                      │                  │
│  12      │   Active Module      │   AI Chat        │
│  Module  │   (Dashboard, etc)   │   Sidebar        │
│  Buttons │                      │                  │
│          │                      │                  │
├──────────┴──────────────────────┴──────────────────┤
│ Status: [DB OK] [APIs 5/6] [Cache 847] [RAM 342MB] │
└──────────────────────────────────────────────────────┘
```

## Navigation

### Left Panel - 12 Modules
Click any module button to switch tabs:
- **Dashboard** - Portfolio overview
- **Watchlist** - Stock monitoring
- **Analyzer** - Graham-Dodd valuation
- **Screener** - Stock screening
- **Macro** - Economic data
- **Journal** - Trading log
- **Thesis** - Investment ideas
- **PDF Intel** - Document analysis
- **Earnings** - Financial data
- **Monitor** - Risk tracking
- **Backtest** - Strategy testing
- **Risk** - Risk metrics

### Right Panel - AI Chat
- Type questions in the input field
- Click quick action buttons for common queries
- AI responses appear in the chat history above

### Top Bar - Market Data
Real-time tickers update every 5 seconds:
- **Green** = Positive gain
- **Red** = Loss

### Menu Bar
- **File**: Settings, Import/Export, Exit
- **Edit**: Copy, Paste, Undo
- **View**: Refresh, Fullscreen, Reset Layout
- **Data**: Fetch quotes, Run screener, Sync database
- **Help**: Documentation, About

## Keyboard Shortcuts (Available Soon)

- `Ctrl+N` - New thesis
- `Ctrl+O` - Open file
- `Ctrl+Q` - Quit
- `Ctrl+L` - Fullscreen
- `F5` - Refresh

## Current State (Phase 3)

✓ Layout is complete  
✓ Navigation works  
✓ Themes applied  
✓ Placeholders ready  

The module panels are **placeholders** - they will be implemented in Phase 4 with actual:
- Data visualization widgets
- Real-time calculations
- API integration
- Database queries

## Next Phase - Module Implementation

Each module will combine:
1. **UI Panel** - Visual components (charts, tables, etc)
2. **Application Layer** - Business logic (use cases)
3. **Domain Layer** - Graham-Dodd formulas
4. **Infrastructure** - API adapters, database

Example of a completed module:

```python
# ui/panels/analyzer_panel.py
from quantum_terminal.application.market import get_fundamentals
from quantum_terminal.domain.valuation import graham_formula

class AnalyzerPanel(QWidget):
    def __init__(self):
        # UI setup...
        
    def analyze_ticker(self, ticker: str):
        # Get data from application layer
        fundamentals = get_fundamentals(ticker)
        
        # Calculate Graham value from domain layer
        value = graham_formula(fundamentals.eps, fundamentals.growth)
        
        # Display in UI
        self.display_valuation(value)
```

## Testing

Run the test suite:

```bash
# All UI tests
pytest tests/test_main_window.py -v

# Specific test class
pytest tests/test_main_window.py::TestNavigationWidget -v

# Single test
pytest tests/test_main_window.py::TestNavigationWidget::test_navigation_item_count -v
```

## Color Theme Reference

### Text
- **Primary** (#E8E8E8) - Main text
- **Secondary** (#888888) - Labels, hints
- **Accent** (#FF6B00) - Highlights, actions

### Status
- **Success** (#00D26A) - Gains, online
- **Error** (#FF3B30) - Losses, offline
- **Warning** (#FFD60A) - Alerts
- **Info** (#0A84FF) - Information

### Background
- **Main** (#0A0A0A) - Window background
- **Panel** (#141414) - Panel backgrounds
- **Widget** (#1E1E1E) - Widget backgrounds
- **Hover** (#262626) - Hover state

## Customization

### Change a Color

In `quantum_terminal/ui/styles/colors.py`:

```python
class Colors:
    ACCENT = "#FF6B00"  # Change this to customize accent color
```

### Modify Stylesheet

Edit `quantum_terminal/ui/styles/bloomberg_dark.qss`:

```qss
/* Change button colors */
QPushButton {
    background-color: #2E7D9A;  /* Default blue */
}

QPushButton:hover {
    background-color: #3a8daa;  /* Lighter on hover */
}
```

### Add a New Module

1. Create panel in `quantum_terminal/ui/panels/my_module.py`
2. Create use case in `application/` layer
3. Add module to `main_window.py`:

```python
# In QuantumTerminal.__init__()
my_panel = MyModulePanel()
self.tabs.add_module_tab("My Module", my_panel)
```

4. Add to navigation module list in `NavigationWidget.__init__()`

## Troubleshooting

### Window won't open
```bash
# Check PyQt6 is installed
pip list | grep PyQt6

# Install if missing
pip install PyQt6
```

### Dark theme not applying
```bash
# Check stylesheet path
ls quantum_terminal/ui/styles/bloomberg_dark.qss

# Check colors.py exists
ls quantum_terminal/ui/styles/colors.py
```

### Chat widget not responding
- Check if message input field is focused
- Verify "Send" button click works
- Check server logs for AI backend errors

### Module tabs not showing
- Verify 12 placeholder modules are initialized
- Check module names in NavigationWidget match tabs
- Review console output for initialization errors

## Architecture Overview

```
main.py (entry point)
  ↓
QuantumTerminal (QMainWindow)
  ├─ MarketBarWidget (ticker bar, top)
  ├─ NavigationWidget (left sidebar)
  ├─ ModulePanelWidget (center tabs)
  │  ├─ Dashboard panel (placeholder)
  │  ├─ Watchlist panel (placeholder)
  │  ├─ Analyzer panel (placeholder)
  │  ├─ ... (9 more)
  │  └─ Risk panel (placeholder)
  ├─ ChatWidget (right sidebar)
  └─ StatusBar (bottom)

Colors & Styling:
  ├─ colors.py (color constants)
  ├─ bloomberg_dark.qss (stylesheet)
  └─ __init__.py (style module init)

Testing:
  └─ tests/test_main_window.py (31 tests)
```

## Performance Tips

1. **Large datasets**: Use pagination in tables
2. **Real-time updates**: Update only changed widgets
3. **Long calculations**: Run in separate threads
4. **API calls**: Cache results with TTL (see CLAUDE.md)

## Integration with Graham-Dodd Methodology

The UI displays valuation results from the domain layer:

- **Analyzer** → Graham Formula value
- **Screener** → Quality score (0-100)
- **Risk** → Manipulation detection, VaR
- **Monitor** → Portfolio risk metrics
- **Journal** → Trade adherence to thesis

All calculations are in `quantum_terminal/domain/`:
- `valuation.py` - Pricing models
- `risk.py` - Quality scoring
- `models.py` - Data structures

## Next: Phase 4 Implementation

Start with one module to establish pattern:

1. **Choose a module** (e.g., Dashboard)
2. **Create UI panel** - Widgets for display
3. **Create use case** - Business logic in application layer
4. **Connect signals** - UI events to use case methods
5. **Test thoroughly** - Unit tests + integration tests
6. **Move to next module**

Expected time per module: **2-3 hours**

Total Phase 4 time: **24-36 hours** (12 modules × 2-3 hours)

---

**Status**: UI ready for integration  
**Next command**: `python main.py`  
**Phase**: 3 (UI Skeleton) → 4 (Module Implementation)
