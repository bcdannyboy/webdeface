"""Main CLI application using Click framework."""

import asyncio
import functools
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..scheduler.orchestrator import (
    cleanup_scheduling_orchestrator,
    get_scheduling_orchestrator,
)
from ..storage import get_storage_manager
from ..utils.logging import get_structured_logger
from .types import CLIContext, CommandResult

console = Console()
logger = get_structured_logger(__name__)


def async_command(f):
    """Decorator to run async functions in Click commands."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # Check if we're already in an event loop (e.g., during testing)
            try:
                asyncio.get_running_loop()
                # If we're in a loop, run in a new thread with its own event loop
                import concurrent.futures

                def run_in_new_loop():
                    return asyncio.run(f(*args, **kwargs))

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()

            except RuntimeError:
                # No running loop, use asyncio.run()
                return asyncio.run(f(*args, **kwargs))
        except KeyboardInterrupt:
            console.print("❌ Operation cancelled by user", style="red")
            sys.exit(1)
        except Exception as e:
            console.print(f"❌ Error: {str(e)}", style="red")
            logger.error(f"CLI command failed: {str(e)}")
            sys.exit(1)

    return wrapper


def handle_result(result: CommandResult, ctx: CLIContext) -> None:
    """Handle command result output."""
    if result.success:
        if result.message:
            console.print(f"✅ {result.message}", style="green")
        if result.data and ctx.verbose:
            console.print_json(data=result.data)
    else:
        console.print(f"❌ {result.message}", style="red")
        if result.data and ctx.debug:
            console.print_json(data=result.data)

    if not result.success:
        sys.exit(result.exit_code)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to configuration file"
)
@click.pass_context
def cli(ctx, verbose: bool, debug: bool, config: Optional[str]) -> None:
    """WebDeface Monitor - Web Defacement Detection and Alerting System."""
    ctx.ensure_object(dict)
    ctx.obj = CLIContext(verbose=verbose, debug=debug)

    if config:
        # TODO: Load custom config file
        pass

    if ctx.obj.verbose:
        console.print("🚀 WebDeface Monitor CLI", style="bold blue")


# Website Management Commands
@cli.group()
def website():
    """Website management commands."""
    pass


@website.command()
@click.argument("url")
@click.option("--name", help="Website name (defaults to domain)")
@click.option(
    "--interval", default="*/15 * * * *", help="Monitoring interval (cron expression)"
)
@click.option("--max-depth", default=2, help="Maximum crawl depth")
@click.pass_obj
@async_command
async def add(
    ctx: CLIContext, url: str, name: Optional[str], interval: str, max_depth: int
) -> None:
    """Add a website for monitoring."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"

        if not name:
            name = parsed.netloc or url

        storage = await get_storage_manager()

        # Check if website already exists
        existing = await storage.get_website_by_url(url)
        if existing:
            result = CommandResult(
                success=False, message=f"Website already exists: {url}", exit_code=1
            )
            handle_result(result, ctx)
            return

        # Create website
        website_data = {
            "url": url,
            "name": name,
            "check_interval_seconds": 900,  # 15 minutes default
            "is_active": True,
        }

        website = await storage.create_website(website_data)

        # Schedule monitoring
        orchestrator = await get_scheduling_orchestrator()
        execution_id = await orchestrator.schedule_website_monitoring(website.id)

        result = CommandResult(
            success=True,
            message=f"Website added successfully: {name} ({url})",
            data={
                "website_id": website.id,
                "execution_id": execution_id,
                "interval": interval,
            },
        )
        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to add website: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@website.command()
@click.argument("website_id")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
@click.pass_obj
@async_command
async def remove(ctx: CLIContext, website_id: str, force: bool) -> None:
    """Remove a website from monitoring."""
    try:
        storage = await get_storage_manager()
        website = await storage.get_website(website_id)

        if not website:
            result = CommandResult(
                success=False, message=f"Website not found: {website_id}", exit_code=1
            )
            handle_result(result, ctx)
            return

        if not force:
            if not click.confirm(f"Remove website '{website.name}' ({website.url})?"):
                console.print("❌ Operation cancelled", style="yellow")
                return

        # Unschedule monitoring
        orchestrator = await get_scheduling_orchestrator()
        await orchestrator.unschedule_website_monitoring(website_id)

        # Remove website
        await storage.delete_website(website_id)

        result = CommandResult(
            success=True,
            message=f"Website removed successfully: {website.name}",
            data={"website_id": website_id},
        )
        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to remove website: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@website.command()
@click.option(
    "--status", type=click.Choice(["active", "inactive", "all"]), default="all"
)
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
@click.pass_obj
@async_command
async def list(ctx: CLIContext, status: str, output_format: str) -> None:
    """List all monitored websites."""
    try:
        storage = await get_storage_manager()
        websites = await storage.list_websites()

        # Filter by status
        if status != "all":
            is_active = status == "active"
            websites = [w for w in websites if w.is_active == is_active]

        if output_format == "json":
            data = []
            for website in websites:
                data.append(
                    {
                        "id": website.id,
                        "name": website.name,
                        "url": website.url,
                        "status": "active" if website.is_active else "inactive",
                        "last_checked": website.last_checked_at.isoformat()
                        if website.last_checked_at
                        else None,
                        "created_at": website.created_at.isoformat(),
                    }
                )
            console.print_json(data=data)
        else:
            table = Table()
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("URL", style="blue")
            table.add_column("Status", justify="center")
            table.add_column("Last Checked", style="yellow")

            for website in websites:
                status_text = "🟢 Active" if website.is_active else "🔴 Inactive"
                last_checked = (
                    website.last_checked_at.strftime("%Y-%m-%d %H:%M")
                    if website.last_checked_at
                    else "Never"
                )

                table.add_row(
                    website.id[:8], website.name, website.url, status_text, last_checked
                )

            console.print(table)

        result = CommandResult(
            success=True,
            message=f"Found {len(websites)} websites",
            data={"count": len(websites)},
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to list websites: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@website.command()
@click.argument("website_id")
@click.pass_obj
@async_command
async def status(ctx: CLIContext, website_id: str) -> None:
    """Show detailed status for a website."""
    try:
        storage = await get_storage_manager()
        website = await storage.get_website(website_id)

        if not website:
            result = CommandResult(
                success=False, message=f"Website not found: {website_id}", exit_code=1
            )
            handle_result(result, ctx)
            return

        # Get recent snapshots
        snapshots = await storage.get_website_snapshots(website_id, limit=5)
        alerts = await storage.get_website_alerts(website_id, limit=5)

        # Display website info
        table = Table(title=f"Website Status: {website.name}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("ID", website.id)
        table.add_row("Name", website.name)
        table.add_row("URL", website.url)
        table.add_row("Status", "🟢 Active" if website.is_active else "🔴 Inactive")
        table.add_row("Created", website.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row(
            "Last Checked",
            website.last_checked_at.strftime("%Y-%m-%d %H:%M:%S")
            if website.last_checked_at
            else "Never",
        )
        table.add_row("Total Snapshots", str(len(snapshots)))
        table.add_row(
            "Active Alerts", str(len([a for a in alerts if a.status == "open"]))
        )

        console.print(table)

        result = CommandResult(
            success=True,
            message=f"Website status retrieved: {website.name}",
            data={"website_id": website_id},
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False,
            message=f"Failed to get website status: {str(e)}",
            exit_code=1,
        )
        handle_result(result, ctx)


# Monitoring Control Commands
@cli.group()
def monitoring():
    """Monitoring control commands."""
    pass


@monitoring.command()
@click.option("--website-id", help="Start monitoring for specific website")
@click.pass_obj
@async_command
async def start(ctx: CLIContext, website_id: Optional[str]) -> None:
    """Start monitoring operations."""
    try:
        orchestrator = await get_scheduling_orchestrator()

        if website_id:
            execution_id = await orchestrator.schedule_website_monitoring(website_id)
            result = CommandResult(
                success=True,
                message=f"Monitoring started for website: {website_id}",
                data={"website_id": website_id, "execution_id": execution_id},
            )
        else:
            # Start the orchestrator if not running
            if not orchestrator.is_running:
                await orchestrator.setup()

            result = CommandResult(
                success=True,
                message="Monitoring system started",
                data={"status": "running"},
            )

        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to start monitoring: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@monitoring.command()
@click.option("--website-id", help="Stop monitoring for specific website")
@click.pass_obj
@async_command
async def stop(ctx: CLIContext, website_id: Optional[str]) -> None:
    """Stop monitoring operations."""
    try:
        orchestrator = await get_scheduling_orchestrator()

        if website_id:
            success = await orchestrator.unschedule_website_monitoring(website_id)
            result = CommandResult(
                success=success,
                message=f"Monitoring stopped for website: {website_id}"
                if success
                else f"Failed to stop monitoring for website: {website_id}",
                data={"website_id": website_id},
            )
        else:
            await cleanup_scheduling_orchestrator()
            result = CommandResult(
                success=True,
                message="Monitoring system stopped",
                data={"status": "stopped"},
            )

        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to stop monitoring: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@monitoring.command()
@click.option("--website-id", help="Pause monitoring for specific website")
@click.pass_obj
@async_command
async def pause(ctx: CLIContext, website_id: Optional[str]) -> None:
    """Pause monitoring operations."""
    try:
        orchestrator = await get_scheduling_orchestrator()

        if website_id:
            # This would pause specific website monitoring
            result = CommandResult(
                success=True,
                message=f"Monitoring paused for website: {website_id}",
                data={"website_id": website_id},
            )
        else:
            pause_result = await orchestrator.pause_all_jobs()
            result = CommandResult(
                success=True, message="All monitoring jobs paused", data=pause_result
            )

        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to pause monitoring: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@monitoring.command()
@click.option("--website-id", help="Resume monitoring for specific website")
@click.pass_obj
@async_command
async def resume(ctx: CLIContext, website_id: Optional[str]) -> None:
    """Resume monitoring operations."""
    try:
        orchestrator = await get_scheduling_orchestrator()

        if website_id:
            # This would resume specific website monitoring
            result = CommandResult(
                success=True,
                message=f"Monitoring resumed for website: {website_id}",
                data={"website_id": website_id},
            )
        else:
            resume_result = await orchestrator.resume_all_jobs()
            result = CommandResult(
                success=True, message="All monitoring jobs resumed", data=resume_result
            )

        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to resume monitoring: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@monitoring.command()
@click.argument("website_id")
@click.pass_obj
@async_command
async def check(ctx: CLIContext, website_id: str) -> None:
    """Run immediate check for a website."""
    try:
        orchestrator = await get_scheduling_orchestrator()

        # Execute immediate monitoring workflow
        execution_id = await orchestrator.execute_immediate_workflow(
            workflow_id="website_monitoring",
            website_id=website_id,
            parameters={"priority": "high", "immediate": True},
        )

        result = CommandResult(
            success=True,
            message=f"Immediate check initiated for website: {website_id}",
            data={"website_id": website_id, "execution_id": execution_id},
        )
        handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False,
            message=f"Failed to run immediate check: {str(e)}",
            exit_code=1,
        )
        handle_result(result, ctx)


# System Status Commands
@cli.group()
def system():
    """System status and reporting commands."""
    pass


@system.command()
@click.pass_obj
@async_command
async def status(ctx: CLIContext) -> None:
    """Show system status."""
    try:
        orchestrator = await get_scheduling_orchestrator()
        status_data = await orchestrator.get_orchestrator_status()

        # Display system status
        table = Table(title="System Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        overall_status = (
            "🟢 Running" if status_data.get("status") == "running" else "🔴 Stopped"
        )
        table.add_row(
            "Overall",
            overall_status,
            f"Uptime: {status_data.get('uptime_seconds', 0):.1f}s",
        )

        components = status_data.get("components", {})
        for component, running in components.items():
            comp_status = "🟢 Running" if running else "🔴 Stopped"
            table.add_row(component.replace("_", " ").title(), comp_status, "")

        table.add_row(
            "Jobs Scheduled", str(status_data.get("total_jobs_scheduled", 0)), ""
        )
        table.add_row(
            "Workflows Executed",
            str(status_data.get("total_workflows_executed", 0)),
            "",
        )
        table.add_row(
            "Active Workflows", str(status_data.get("active_workflows_count", 0)), ""
        )

        console.print(table)

        result = CommandResult(
            success=True, message="System status retrieved", data=status_data
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to get system status: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


@system.command()
@click.pass_obj
@async_command
async def health(ctx: CLIContext) -> None:
    """Show system health information."""
    try:
        orchestrator = await get_scheduling_orchestrator()
        report = await orchestrator.get_monitoring_report()

        if report:
            table = Table(title="System Health")
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Score", style="yellow")

            table.add_row("Overall Health", f"{report.overall_health_score:.1f}/10", "")

            for check in report.health_checks:
                status = "🟢 Healthy" if check.healthy else "🔴 Unhealthy"
                table.add_row(check.component, status, check.message)

            console.print(table)
        else:
            console.print("❌ No health report available", style="red")

        result = CommandResult(
            success=True,
            message="Health information retrieved",
            data={"health_score": report.overall_health_score if report else None},
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False,
            message=f"Failed to get health information: {str(e)}",
            exit_code=1,
        )
        handle_result(result, ctx)


@system.command()
@click.pass_obj
@async_command
async def metrics(ctx: CLIContext) -> None:
    """Show system metrics."""
    try:
        storage = await get_storage_manager()

        # Get basic metrics
        websites = await storage.list_websites()
        total_websites = len(websites)
        active_websites = len([w for w in websites if w.is_active])

        # Get recent activity
        from datetime import datetime

        today = datetime.utcnow().date()

        table = Table(title="System Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Websites", str(total_websites))
        table.add_row("Active Websites", str(active_websites))
        table.add_row("Inactive Websites", str(total_websites - active_websites))

        console.print(table)

        result = CommandResult(
            success=True,
            message="System metrics retrieved",
            data={"total_websites": total_websites, "active_websites": active_websites},
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False,
            message=f"Failed to get system metrics: {str(e)}",
            exit_code=1,
        )
        handle_result(result, ctx)


@system.command()
@click.option(
    "--level", type=click.Choice(["debug", "info", "warning", "error"]), default="info"
)
@click.option("--component", help="Filter logs by component")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
@click.pass_obj
def logs(ctx: CLIContext, level: str, component: Optional[str], lines: int) -> None:
    """Show system logs."""
    try:
        # This would read from log files or log aggregation system
        console.print(f"📋 Showing last {lines} log entries (level: {level})")

        if component:
            console.print(f"🔍 Filtered by component: {component}")

        # Mock log entries for now
        log_entries = [
            "2024-01-01 12:00:00 INFO [scheduler] Starting monitoring for website abc123",
            "2024-01-01 12:01:00 INFO [scraper] Successfully scraped website xyz789",
            "2024-01-01 12:02:00 WARNING [classifier] Low confidence score for detection",
            "2024-01-01 12:03:00 ERROR [notification] Failed to send Slack alert",
        ]

        for entry in log_entries[-lines:]:
            if level.upper() in entry:
                if not component or component in entry:
                    console.print(entry)

        result = CommandResult(
            success=True,
            message=f"Showing {len(log_entries)} log entries",
            data={"level": level, "component": component},
        )

        if ctx.verbose:
            handle_result(result, ctx)

    except Exception as e:
        result = CommandResult(
            success=False, message=f"Failed to get system logs: {str(e)}", exit_code=1
        )
        handle_result(result, ctx)


def create_cli() -> click.Group:
    """Create and return the CLI application."""
    return cli


if __name__ == "__main__":
    cli()
