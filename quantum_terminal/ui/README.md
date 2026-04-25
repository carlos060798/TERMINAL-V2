# Quantum Terminal UI Module

PyQt6-based user interface for Quantum Investment Terminal with Bloomberg-inspired dark theme.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│       Market Ticker Bar (S&P, NASD, BTC, etc)       │
├─────────────────────────────────────────────────────┤
│ Menu: File | Edit | View | Data | Help              │
├──────────────┬──────────────────────┬────────────────┤
│              │                      │                │
│ Navigation   │  Module Panels       │  AI Chat       │
│ (12 modules) │  (QTabWidget)        │  (Sidebar)     │
│              │                      │                │
│ • Dashboard  │  ┌────────────────┐  │ • Message box  │
│ • Watchlist  │  │ Active Module  │  │ • Input field  │
│ • Analyzer   │  │   Content      │  │ • Quick actions│
│ • Screener   │  │                │  │                │
│ • Macro      │  │                │  │                │
│ • Journal    │  └────────────────┘  │                │
│ • Thesis     │                      │                │
│ • PDF Intel  │                      │                │
│ • Earnings   │                      │                │
│ • Monitor    │                      │                │
│ • Backtest   │                      │                │
│ • Risk       │                      │                │
├──────────────┴──────────────────────┴────────────────┤
│ Status Bar: [DB] [APIs] [Cache] [RAM]                │
└──────────────────────────────────────────────────────┘
```

## Files

### Core Components

- **main_window.py** (680+ lines)
  - `QuantumTerminal` - Main window class
  - `MarketBarWidget` - Real-time market ticker bar
  - `NavigationWidget` - Left sidebar with 12 modules
  - `ChatWidget` - Right sidebar AI assistant
  - `ModulePanelWidget` - Central tab widget for modules

### Styling

- **styles/colors.py** - Centralized color palette
  - `Colors` class with 60+ color constants
  - Helper methods for RGB/Hex conversion, interpolation, alpha
  
- **styles/bloomberg_dark.qss** - Complete QSS stylesheet
  - Dark theme (inspired by Bloomberg Terminal)
  - Custom styles for all PyQt6 widgets
  - Hover/focus/pressed states
  - Responsive layout

- **styles/__init__.py** - Style module initialization
  - `load_stylesheet()` - Load QSS from file

### Testing

- **tests/test_main_window.py** (420+ lines)
  - 30+ test cases covering:
    - Window creation and geometry
    - Component initialization
    - Signal emissions
    - Layout integrity
    - Integration tests

## Color Palette

### Background Colors
- **#0A0A0A** - Main background (deep black)
- **#141414** - Panel/frame background
- **#1E1E1E** - Widget background
- **#262626** - Hover state

### Action Colors
- **#FF6B00** - Accent orange (primary action)
- **#00D26A** - Success green
- **#FF3B30** - Error red
- **#FFD60A** - Warning yellow
- **#0A84FF** - Info blue

### Text Colors
- **#E8E8E8** - Primary text
- **#888888** - Secondary text
- **#555555** - Tertiary text
- **#0A0A0A** - Inverse (on light backgrounds)

## Usage

### Launch the Application

```bash
python main.py
```

### Create Custom Module Panel

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from quantum_terminal.ui.styles import Colors

class CustomModule(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        label = QLabel("My Custom Module")
        label.setStyleSheet(f"color: {Colors.ACCENT};")
        layout.addWidget(label)

# Add to window
window.tabs.add_module_tab("Custom", CustomModule())
```

### Send Chat Message Programmatically

```python
window.chat.add_message("Assistant", "Analysis complete!")
```

### Update Market Indices

```python
updates = {
    "S&P 500": {"value": "4,500.00", "change": "+0.25%", "positive": True}
}
window.market_bar.update_indices(updates)
```

## Testing

Run all UI tests:

```bash
pytest tests/test_main_window.py -v
```

Run specific test class:

```bash
pytest tests/test_main_window.py::TestNavigationWidget -v
```

## Key Features

### 3-Column Bloomberg Layout
- **Left (15%)** - Navigation with 12 module buttons
- **Center (70%)** - Active module content (QTabWidget)
- **Right (15%)** - AI chat assistant sidebar

### Real-time Market Data
- Top ticker bar with key indices (S&P, NASD, BTC, WTI, 10Y, VIX, DXY)
- 5-second update timer
- Color-coded positive/negative changes

### Menu System
- **File**: New, Open, Import, Export, Settings, Exit
- **Edit**: Undo, Redo, Copy, Paste
- **View**: Refresh, Fullscreen, Reset Layout
- **Data**: Fetch Quotes, Run Screener, Sync Database
- **Help**: Documentation, About

### Status Bar
- Database connection status
- API availability (5/6)
- Cache item count
- Memory usage

### AI Chat Sidebar
- Message history display
- Text input field
- Quick action buttons
- Error message display

## Integration with Application Layer

Each module panel in the UI should:

1. Import use case from `application/` layer
2. Connect UI events to use case methods
3. Display results in widgets

Example:

```python
from quantum_terminal.application.market import get_quote

class DashboardModule(QWidget):
    def __init__(self):
        super().__init__()
        # UI setup...
        
    def fetch_quote(self, ticker):
        quote = get_quote(ticker)
        self.display_quote(quote)
```

## Development Workflow

### Phase 3: UI Implementation (Current)
1. Main window created ✓
2. Blueprint panels created ✓
3. Signal/slot connections established ✓
4. Tests written ✓

### Phase 4+: Module Implementation
For each module (Dashboard, Watchlist, etc.):

1. Create module panel widget in `ui/panels/`
2. Import use case from `application/`
3. Connect signals to use case methods
4. Display results using data visualization widgets
5. Add tests

## Performance Considerations

- **Lazy loading**: Module panels loaded on-demand
- **Caching**: Market bar data cached with TTL
- **Threading**: Long-running tasks (API calls) run in separate threads
- **Optimization**: QSS compiled once at startup, not per-widget

## Troubleshooting

### Window won't display
```bash
# Check PyQt6 installation
python -c "from PyQt6.QtWidgets import QApplication; print('OK')"
```

### Stylesheet not loading
```bash
# Verify path exists
ls -la quantum_terminal/ui/styles/bloomberg_dark.qss
```

### Module tabs not showing
- Check that `main_window._init_placeholder_modules()` runs
- Verify `ModulePanelWidget.add_module_tab()` is called

## Future Enhancements

- [ ] Dockable panels
- [ ] Customizable toolbar
- [ ] Window state persistence
- [ ] Dark/Light theme toggle
- [ ] Multi-monitor support
- [ ] Keyboard shortcuts customization
- [ ] Workspace management

## References

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Qt Designer](https://doc.qt.io/qt-6/qtdesigner-manual.html)
- [Bloomberg Terminal](https://www.bloomberg.com/professional/product/terminal/)
