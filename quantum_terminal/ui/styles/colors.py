"""Central color palette for Quantum Investment Terminal Bloomberg dark theme."""

from pathlib import Path


class Colors:
    """Color constants for the Bloomberg dark theme."""

    # ============================================================================
    # BACKGROUND COLORS
    # ============================================================================
    BACKGROUND_MAIN = "#0A0A0A"      # Main window background (deep black)
    BACKGROUND_PANEL = "#141414"     # Panel/frame background (dark gray)
    BACKGROUND_WIDGET = "#1E1E1E"    # Widget background (slightly lighter)
    BACKGROUND_HOVER = "#262626"     # Hover state background
    BACKGROUND_SELECTED = "#2A2A2A"  # Selected/highlighted background

    # ============================================================================
    # BORDER & OUTLINE COLORS
    # ============================================================================
    BORDER = "#2A2A2A"               # Standard border
    BORDER_FOCUS = "#FF6B00"          # Focused border (accent color)
    BORDER_DISABLED = "#1F1F1F"       # Disabled border

    # ============================================================================
    # TEXT COLORS
    # ============================================================================
    TEXT_PRIMARY = "#E8E8E8"          # Primary text (warm white)
    TEXT_SECONDARY = "#888888"        # Secondary text (medium gray)
    TEXT_TERTIARY = "#555555"         # Tertiary text (dark gray)
    TEXT_DISABLED = "#3A3A3A"         # Disabled text
    TEXT_INVERSE = "#0A0A0A"          # Text on light backgrounds

    # ============================================================================
    # ACTION COLORS
    # ============================================================================
    ACCENT = "#FF6B00"                # Orange accent (primary action)
    ACCENT_HOVER = "#FF8533"          # Orange hover (lighter)
    ACCENT_DARK = "#CC5500"           # Orange pressed (darker)

    SUCCESS = "#00D26A"               # Green for gains/success
    SUCCESS_DARK = "#00A652"          # Green pressed

    ERROR = "#FF3B30"                 # Red for losses/errors
    ERROR_DARK = "#CC2E26"            # Red pressed

    WARNING = "#FFD60A"               # Yellow for warnings/alerts
    WARNING_DARK = "#CCA806"          # Yellow pressed

    INFO = "#0A84FF"                  # Blue for information
    INFO_DARK = "#0863CC"             # Blue pressed

    # ============================================================================
    # CHART COLORS
    # ============================================================================
    CHART_UP = "#00D26A"              # Candle/bar up color (green)
    CHART_DOWN = "#FF3B30"            # Candle/bar down color (red)
    CHART_NEUTRAL = "#888888"         # Neutral/no-change color (gray)
    CHART_LINE = "#0A84FF"            # Line chart color (blue)
    CHART_GRID = "#262626"            # Grid line color

    # ============================================================================
    # DATA VISUALIZATION
    # ============================================================================
    POSITIVE = "#00D26A"              # Positive metrics (green)
    NEGATIVE = "#FF3B30"              # Negative metrics (red)
    NEUTRAL = "#888888"               # Neutral metrics (gray)
    HIGHLIGHT = "#FF6B00"             # Highlighted data (orange)

    # ============================================================================
    # TRANSPARENCY VARIANTS
    # ============================================================================
    # Used for overlays, tooltips, disabled states
    ACCENT_TRANSPARENT = "rgba(255, 107, 0, 0.1)"
    SUCCESS_TRANSPARENT = "rgba(0, 210, 106, 0.1)"
    ERROR_TRANSPARENT = "rgba(255, 59, 48, 0.1)"
    WARNING_TRANSPARENT = "rgba(255, 214, 10, 0.1)"

    @staticmethod
    def get_stylesheet() -> str:
        """Load and return the Bloomberg dark QSS stylesheet.

        Returns:
            str: The complete QSS stylesheet content.

        Raises:
            FileNotFoundError: If bloomberg_dark.qss is not found.
        """
        stylesheet_path = Path(__file__).parent / "bloomberg_dark.qss"
        if not stylesheet_path.exists():
            raise FileNotFoundError(
                f"Stylesheet not found at {stylesheet_path}"
            )
        return stylesheet_path.read_text(encoding="utf-8")

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB values to hexadecimal color code.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)

        Returns:
            str: Hexadecimal color code (e.g., "#FF6B00")
        """
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hexadecimal color code to RGB values.

        Args:
            hex_color: Hexadecimal color code (e.g., "#FF6B00")

        Returns:
            tuple: (r, g, b) values (0-255 each)

        Raises:
            ValueError: If hex_color is invalid format.
        """
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {hex_color}")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def lerp_color(color1: str, color2: str, t: float) -> str:
        """Linear interpolate between two colors.

        Args:
            color1: First hexadecimal color code
            color2: Second hexadecimal color code
            t: Interpolation factor (0.0 to 1.0)

        Returns:
            str: Interpolated color as hexadecimal code
        """
        r1, g1, b1 = Colors.hex_to_rgb(color1)
        r2, g2, b2 = Colors.hex_to_rgb(color2)

        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)

        return Colors.rgb_to_hex(r, g, b)

    @staticmethod
    def with_alpha(hex_color: str, alpha: float) -> str:
        """Convert hex color to RGBA with specified alpha.

        Args:
            hex_color: Hexadecimal color code
            alpha: Alpha value (0.0 to 1.0)

        Returns:
            str: RGBA color string (e.g., "rgba(255, 107, 0, 0.5)")
        """
        r, g, b = Colors.hex_to_rgb(hex_color)
        return f"rgba({r}, {g}, {b}, {alpha})"
