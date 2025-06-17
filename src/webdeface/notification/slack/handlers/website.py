"""Website management command handlers for Slack."""

from typing import Any
from urllib.parse import urlparse

from ....cli.types import CLIContext, CommandResult
from ....scheduler.orchestrator import get_scheduling_orchestrator
from ....storage import get_storage_manager
from ....utils.logging import get_structured_logger
from ..permissions import Permission
from .base import AsyncCommandMixin, BaseSlackHandler

logger = get_structured_logger(__name__)


class WebsiteHandler(BaseSlackHandler, AsyncCommandMixin):
    """Handles website management commands from Slack."""

    def get_required_permissions(self, subcommands: list[str]) -> list[Permission]:
        """Get required permissions for website commands."""
        if len(subcommands) < 2:
            return [Permission.VIEW_SITES]

        command = subcommands[1]

        permission_map = {
            "add": [Permission.ADD_SITES],
            "remove": [Permission.REMOVE_SITES],
            "list": [Permission.VIEW_SITES],
            "status": [Permission.VIEW_SITES],
        }

        return permission_map.get(command, [Permission.VIEW_SITES])

    async def _execute_command(
        self,
        subcommands: list[str],
        args: dict[str, Any],
        flags: dict[str, Any],
        global_flags: dict[str, Any],
        user_id: str,
    ) -> CommandResult:
        """Execute website command logic."""
        if len(subcommands) < 2:
            return CommandResult(
                success=False,
                message="Website subcommand required (add, remove, list, status)",
                exit_code=1,
            )

        command = subcommands[1]
        cli_context = self.create_cli_context(global_flags, user_id)

        try:
            if command == "add":
                return await self._handle_add(args, flags, cli_context)
            elif command == "remove":
                return await self._handle_remove(args, flags, cli_context)
            elif command == "list":
                return await self._handle_list(args, flags, cli_context)
            elif command == "status":
                return await self._handle_status(args, flags, cli_context)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown website command: {command}",
                    exit_code=1,
                )
        except Exception as e:
            logger.error(
                "Website command execution failed", command=command, error=str(e)
            )
            return CommandResult(
                success=False, message=f"Command failed: {str(e)}", exit_code=1
            )

    async def _handle_add(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle website add command."""
        # Get URL from args
        if 0 not in args:
            return CommandResult(
                success=False,
                message="URL is required for website add command",
                exit_code=1,
            )

        url = str(args[0])

        # Parse URL and add protocol if missing
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"

        # Get optional parameters
        name = flags.get("name")
        if not name:
            name = parsed.netloc or url

        interval = flags.get("interval", 900)  # Default 15 minutes
        max_depth = flags.get("max-depth", 2)

        try:
            storage = await get_storage_manager()

            # Check if website already exists
            existing = await storage.get_website_by_url(url)
            if existing:
                return CommandResult(
                    success=False, message=f"Website already exists: {url}", exit_code=1
                )

            # Create website
            website_data = {
                "url": url,
                "name": name,
                "check_interval_seconds": interval,
                "is_active": True,
            }

            website = await storage.create_website(website_data)

            # Schedule monitoring
            orchestrator = await get_scheduling_orchestrator()
            execution_id = await orchestrator.schedule_website_monitoring(website.id)

            return CommandResult(
                success=True,
                message=f"Website added successfully: {name} ({url})",
                data={
                    "website_id": website.id,
                    "execution_id": execution_id,
                    "interval": interval,
                    "website": {
                        "id": website.id,
                        "name": website.name,
                        "url": website.url,
                        "is_active": website.is_active,
                        "created_at": website.created_at.isoformat(),
                    },
                },
            )

        except Exception as e:
            return CommandResult(
                success=False, message=f"Failed to add website: {str(e)}", exit_code=1
            )

    async def _handle_remove(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle website remove command."""
        if 0 not in args:
            return CommandResult(
                success=False,
                message="Website ID is required for remove command",
                exit_code=1,
            )

        website_id = str(args[0])
        force = flags.get("force", False)

        try:
            storage = await get_storage_manager()
            website = await storage.get_website(website_id)

            if not website:
                return CommandResult(
                    success=False,
                    message=f"Website not found: {website_id}",
                    exit_code=1,
                )

            # For Slack, we skip the confirmation prompt and treat it as forced
            # The confirmation can be handled through Slack interactive components if needed

            # Unschedule monitoring
            orchestrator = await get_scheduling_orchestrator()
            await orchestrator.unschedule_website_monitoring(website_id)

            # Remove website
            await storage.delete_website(website_id)

            return CommandResult(
                success=True,
                message=f"Website removed successfully: {website.name}",
                data={
                    "website_id": website_id,
                    "website_name": website.name,
                    "website_url": website.url,
                },
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to remove website: {str(e)}",
                exit_code=1,
            )

    async def _handle_list(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle website list command."""
        status_filter = flags.get("status", "all")
        output_format = flags.get("format", "table")

        try:
            storage = await get_storage_manager()
            websites = await storage.list_websites()

            # Filter by status
            if status_filter != "all":
                is_active = status_filter == "active"
                websites = [w for w in websites if w.is_active == is_active]

            # Convert to dict format for consistent handling
            website_data = []
            for website in websites:
                website_dict = {
                    "id": website.id,
                    "name": website.name,
                    "url": website.url,
                    "is_active": website.is_active,
                    "last_checked_at": website.last_checked_at.isoformat()
                    if website.last_checked_at
                    else None,
                    "created_at": website.created_at.isoformat(),
                    "check_interval_seconds": website.check_interval_seconds,
                }
                website_data.append(website_dict)

            return CommandResult(
                success=True,
                message=f"Found {len(websites)} websites",
                data={
                    "websites": website_data,
                    "total": len(websites),
                    "filter": status_filter,
                    "format": output_format,
                },
            )

        except Exception as e:
            return CommandResult(
                success=False, message=f"Failed to list websites: {str(e)}", exit_code=1
            )

    async def _handle_status(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle website status command."""
        if 0 not in args:
            return CommandResult(
                success=False,
                message="Website ID is required for status command",
                exit_code=1,
            )

        website_id = str(args[0])

        try:
            storage = await get_storage_manager()
            website = await storage.get_website(website_id)

            if not website:
                return CommandResult(
                    success=False,
                    message=f"Website not found: {website_id}",
                    exit_code=1,
                )

            # Get recent snapshots and alerts
            snapshots = await storage.get_website_snapshots(website_id, limit=5)
            alerts = await storage.get_website_alerts(website_id, limit=5)

            # Format website status data
            status_data = {
                "website": {
                    "id": website.id,
                    "name": website.name,
                    "url": website.url,
                    "is_active": website.is_active,
                    "created_at": website.created_at.isoformat(),
                    "last_checked_at": website.last_checked_at.isoformat()
                    if website.last_checked_at
                    else None,
                    "check_interval_seconds": website.check_interval_seconds,
                },
                "snapshots": {
                    "total_count": len(snapshots),
                    "recent": [
                        {
                            "id": s.id,
                            "captured_at": s.captured_at.isoformat(),
                            "status_code": s.status_code,
                            "response_time_ms": s.response_time_ms,
                            "content_hash": s.content_hash,
                        }
                        for s in snapshots
                    ],
                },
                "alerts": {
                    "total_count": len(alerts),
                    "active_count": len([a for a in alerts if a.status == "open"]),
                    "recent": [
                        {
                            "id": a.id,
                            "title": a.title,
                            "severity": a.severity,
                            "status": a.status,
                            "created_at": a.created_at.isoformat(),
                        }
                        for a in alerts
                    ],
                },
            }

            return CommandResult(
                success=True,
                message=f"Website status retrieved: {website.name}",
                data=status_data,
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to get website status: {str(e)}",
                exit_code=1,
            )


# Export the handler class
__all__ = ["WebsiteHandler"]
