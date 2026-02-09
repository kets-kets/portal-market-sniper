"""
Application Layer: UI Dashboard
Renders real-time state using 'rich' library.
"""
import datetime
from typing import List, Dict, Optional
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich import box
from rich.text import Text

from src.domain import Collection, NFT, Money

# ...

class DashboardService:
    """
    Manages the terminal UI.
    Uses rich.live to update the screen without flickering.
    """
    def __init__(self, collections: List[Collection]) -> None:
        self.console = Console()
        self.collections = collections
        self.layout = Layout()
        self.start_time = datetime.datetime.now()
        
        # State
        self.floors: Dict[str, Dict[str, float]] = {}
        self.last_scan_time = datetime.datetime.now()
        self.cycle_count = 0
        self.logs: List[str] = []
        self.active = False
        self._live: Optional[Live] = None
        self._analytics_cache: Dict[str, Dict[str, float]] = {}

    def start(self) -> None:
        """Starts the Live display context"""
        self.active = True
        self._init_layout()
        self._live = Live(self.layout, refresh_per_second=4, screen=True)
        self._live.start()

    def stop(self) -> None:
        """Stops the Live display"""
        self.active = False
        if self._live:
            self._live.stop()

    def update_state(
        self,
        floors: Dict[str, Dict[str, float]],
        cycle_count: int,
        analytics_cache: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        """Updates internal state and refreshes layout"""
        self.floors = floors
        self.cycle_count = cycle_count
        self.last_scan_time = datetime.datetime.now()
        
        if analytics_cache is not None:
            self._analytics_cache = analytics_cache
        
        self._update_layout()

    def add_log(self, message: str, level: str = "INFO") -> None:
        """Adds a log message to the log panel"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        color = "green"
        if level == "WARNING": color = "yellow"
        if level == "ERROR": color = "red"
        
        formatted_msg = f"[{color}][{timestamp}] {message}[/{color}]"
        self.logs.append(formatted_msg)
        if len(self.logs) > 10: # Keep last 10 logs
            self.logs.pop(0)
        
        # Trigger layout update if running
        if self.active:
            self._update_layout()

    def _init_layout(self) -> None:
        """Splits screen into sections"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="analytics", size=6),
            Layout(name="footer", size=6)
        )

    def _update_layout(self) -> None:
        """Re-renders all panels"""
        self.layout["header"].update(self._make_header())
        self.layout["main"].update(self._make_table())
        self.layout["analytics"].update(self._make_analytics_panel())
        self.layout["footer"].update(self._make_log_panel())

    def _make_header(self) -> Panel:
        uptime = str(datetime.datetime.now() - self.start_time).split('.')[0]
        total_models = sum(len(c.models) for c in self.collections)
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        grid.add_row(
            f"🚀 [bold blue]NFT Sniper Bot[/bold blue] | Cycles: {self.cycle_count}",
            f"Targeting [bold green]{total_models}[/bold green] Models | Uptime: {uptime}"
        )
        return Panel(grid, style="white on blue")

    def _make_table(self) -> Panel:
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("Collection", style="cyan", no_wrap=True)
        table.add_column("Model", style="white")
        table.add_column("Floor Price", justify="right", style="green")
        table.add_column("Status", justify="center")

        has_data = False
        
        for col in self.collections:
            floors = self.floors.get(col.short_name, {})
            # Only show models tracked in config or all found?
            # Showing models from Collection config
            for model_name in col.models:
                price = floors.get(model_name)
                price_display = f"{price} TON" if price else "-"
                status = "🟢 Monitoring" if price else "🔴 No Data"
                
                table.add_row(
                    col.name,
                    model_name,
                    price_display,
                    status
                )
                has_data = True
            
            # Add separator between collections
            if col != self.collections[-1]:
                table.add_section()

        if not has_data:
             table.add_row("Waiting for data...", "", "", "")

        return Panel(table, title="Market Overview", border_style="blue")

    def _make_log_panel(self) -> Panel:
        log_text = "\n".join(self.logs)
        return Panel(Text.from_markup(log_text), title="Activity Log", border_style="grey50")


    
    def _make_analytics_panel(self) -> Panel:
        """Analytics panel - shows cached data from monitor"""
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Collection", style="cyan", width=20)
        table.add_column("Velocity 24h", justify="center", width=12)
        table.add_column("Status", justify="center", width=15)
        
        # Get cache from monitor (if exists)
        analytics_cache = getattr(self, '_analytics_cache', {})
        
        for collection in self.collections[:2]:
            data = analytics_cache.get(collection.short_name)
            
            if data:
                velocity = data.get('velocity', 0)
                trending_score = data.get('trending_score', 1.0)
                
                if trending_score >= 1.5:
                    status = "🔥 TRENDING"
                elif velocity >= 5:
                    status = "🟢 Active"
                else:
                    status = "⚪ Low"
                
                table.add_row(collection.name, str(velocity), status)
            else:
                table.add_row(collection.name, "...", "⏳ Loading")
        
        return Panel(table, title="📊 Market Analytics (Portal API)", border_style="green", box=box.ROUNDED)
