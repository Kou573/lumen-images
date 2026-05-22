"""
Lumen Industries — CEO Interface

Multi-agent content business orchestration system.
The user acts as CEO; the COO and department agents do the work.

Usage:
    python main.py
    python main.py "AIツールのトップ10のアフィリエイト記事を日本語で書いて"
    python main.py "Write a top-10 AI tools affiliate blog post"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from config import COMPANY_NAME, OUTPUT_DIR

console = Console()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_banner() -> None:
    """Print the Lumen Industries banner."""
    banner = Text()
    banner.append("  ██╗     ██╗   ██╗███╗   ███╗███████╗███╗   ██╗\n", style="bold cyan")
    banner.append("  ██║     ██║   ██║████╗ ████║██╔════╝████╗  ██║\n", style="bold cyan")
    banner.append("  ██║     ██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║\n", style="bold cyan")
    banner.append("  ██║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║\n", style="bold cyan")
    banner.append("  ███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║\n", style="bold cyan")
    banner.append("  ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝\n", style="bold cyan")
    banner.append(f"\n   {COMPANY_NAME} — AI Content Business Platform\n", style="bold white")

    console.print(Panel(Align.center(banner), border_style="cyan", padding=(1, 4)))
    console.print()


def print_org_chart() -> None:
    """Print the company organizational chart."""
    console.print(Rule("[bold yellow]Company Organization Chart[/bold yellow]"))
    console.print()

    tree = Tree(
        "[bold green]👤 CEO (You)[/bold green]",
        guide_style="bold bright_black",
    )

    coo_branch = tree.add("[bold blue]🏢 COO — Chief Operations Officer[/bold blue] [dim](claude-opus-4-7 + adaptive thinking)[/dim]")

    research = coo_branch.add("[bold magenta]🔬 Research Director[/bold magenta] [dim](claude-sonnet-4-6)[/dim]")
    research.add("[dim]📊 Trend Analyzer Worker (claude-haiku-4-5)[/dim]")
    research.add("[dim]🔑 Keyword Research Worker (claude-haiku-4-5)[/dim]")

    content = coo_branch.add("[bold yellow]✍️  Content Director[/bold yellow] [dim](claude-sonnet-4-6)[/dim]")
    content.add("[dim]📝 Writer Worker (claude-sonnet-4-6)[/dim]")
    content.add("[dim]🔍 SEO Optimizer Worker (claude-haiku-4-5)[/dim]")

    marketing = coo_branch.add("[bold cyan]📣 Marketing Director[/bold cyan] [dim](claude-sonnet-4-6)[/dim]")
    marketing.add("[dim]📱 Social Media Worker (claude-haiku-4-5)[/dim]")

    sales = coo_branch.add("[bold red]💰 Sales Director[/bold red] [dim](claude-sonnet-4-6)[/dim]")
    sales.add("[dim]💵 Monetization Worker (claude-haiku-4-5)[/dim]")

    console.print(tree)
    console.print()


def print_workflow_table() -> None:
    """Print the typical workflow steps."""
    table = Table(
        title="Standard Workflow",
        box=box.ROUNDED,
        border_style="dim",
        show_lines=True,
    )
    table.add_column("Step", style="bold", width=6, justify="center")
    table.add_column("Department", style="bold cyan", width=22)
    table.add_column("Deliverable", style="white")

    table.add_row("1", "Research Department", "Trending topics + profitable SEO keywords")
    table.add_row("2", "Content Department", "1,500-word SEO article with affiliate angles")
    table.add_row("3", "Marketing Department", "Social media posts for 5 platforms")
    table.add_row("4", "Sales Department", "Affiliate programs + revenue projections")
    table.add_row("5", "COO", "Executive summary → saved to output/")

    console.print(table)
    console.print()


def print_department_call(dept: str, task_preview: str) -> None:
    """Show which department the COO is calling."""
    dept_styles = {
        "Research": ("magenta", "🔬"),
        "Content": ("yellow", "✍️ "),
        "Marketing": ("cyan", "📣"),
        "Sales": ("red", "💰"),
    }
    style, emoji = dept_styles.get(dept, ("white", "•"))
    preview = task_preview[:80] + "..." if len(task_preview) > 80 else task_preview
    console.print(
        Panel(
            f"[dim]{preview}[/dim]",
            title=f"{emoji}  [{style}]COO → {dept} Department[/{style}]",
            border_style=style,
            padding=(0, 2),
        )
    )


def print_result(section: str, content: str, style: str = "green") -> None:
    """Print a result section."""
    console.print(
        Panel(
            content[:2000] + ("\n[dim]...(truncated, full output saved to file)[/dim]" if len(content) > 2000 else ""),
            title=f"[bold {style}]{section}[/bold {style}]",
            border_style=style,
            padding=(1, 2),
        )
    )
    console.print()


# ---------------------------------------------------------------------------
# Instrumented COO wrapper that shows Rich output during execution
# ---------------------------------------------------------------------------

class InstrumentedCOO:
    """
    Thin wrapper around COO that intercepts department calls and
    displays Rich progress output without modifying the core agent code.
    """

    def __init__(self) -> None:
        # Import here so config is already loaded
        from agents.coo import COO
        self._coo = COO()
        self._dept_map = {
            "call_research_department": "Research",
            "call_content_department": "Content",
            "call_marketing_department": "Marketing",
            "call_sales_department": "Sales",
        }
        # Monkey-patch _execute_tool to add display
        original_execute = self._coo._execute_tool

        def instrumented_execute(tool_name: str, tool_input: dict) -> str:
            dept = self._dept_map.get(tool_name, tool_name)
            task_preview = tool_input.get("task", "")
            print_department_call(dept, task_preview)
            with Status(
                f"[bold]  {dept} Department working...[/bold]",
                console=console,
                spinner="dots",
            ):
                result = original_execute(tool_name, tool_input)
            console.print(f"  [green]✓[/green] {dept} Department completed.\n")
            return result

        self._coo._execute_tool = instrumented_execute  # type: ignore[method-assign]

    def execute_ceo_goal(self, goal: str) -> str:
        return self._coo.execute_ceo_goal(goal)

    @property
    def last_output_path(self) -> Path | None:
        return getattr(self._coo, "_last_output_path", None)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print_banner()
    print_org_chart()
    print_workflow_table()

    # Get CEO goal from CLI arg or prompt
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
        console.print(f"[bold]CEO Goal (from CLI):[/bold] {goal}\n")
    else:
        console.print(Rule("[bold green]CEO Input[/bold green]"))
        console.print(
            "[dim]Examples:\n"
            '  "Write an AI tools affiliate blog post"\n'
            '  "AIツールのトップ10のアフィリエイト記事を日本語で書いて"\n'
            '  "Create a personal finance beginner\'s guide with affiliate links"[/dim]\n'
        )
        goal = Prompt.ask("[bold green]Enter your goal[/bold green]")

    if not goal.strip():
        console.print("[red]No goal provided. Exiting.[/red]")
        sys.exit(1)

    console.print()
    console.print(Rule("[bold blue]COO Orchestration in Progress[/bold blue]"))
    console.print(
        f"[dim]The COO is analyzing your goal and coordinating departments...[/dim]\n"
    )

    start_time = time.time()

    coo = InstrumentedCOO()

    with Status("[bold blue]COO thinking (adaptive reasoning)...[/bold blue]", console=console, spinner="bouncingBar"):
        # We wrap only the first run call to show the top-level thinking spinner.
        # The instrumented tool calls will show individual department spinners.
        pass  # Status exits immediately; actual call below

    try:
        result = coo.execute_ceo_goal(goal)
    except Exception as exc:
        console.print(f"\n[bold red]Error during execution:[/bold red] {exc}")
        raise

    elapsed = time.time() - start_time

    # Display final result
    console.print()
    console.print(Rule("[bold green]COO Executive Report[/bold green]"))
    print_result("Executive Report to CEO", result, style="green")

    # Output location
    output_path = coo.last_output_path
    if output_path and output_path.exists():
        console.print(
            Panel(
                f"[bold]All deliverables saved to:[/bold]\n"
                f"[cyan]{output_path}[/cyan]\n\n"
                f"Files:\n"
                + "\n".join(f"  • {f.name}" for f in sorted(output_path.iterdir())),
                title="[bold]Output Files[/bold]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
    else:
        console.print(
            Panel(
                f"[cyan]{OUTPUT_DIR}[/cyan]",
                title="[bold]Output Directory[/bold]",
                border_style="cyan",
            )
        )

    console.print()
    console.print(
        f"[dim]Total execution time: {elapsed:.1f}s[/dim]"
    )
    console.print(
        Panel(
            "[bold green]Mission complete.[/bold green] Lumen Industries is ready to generate revenue.",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
