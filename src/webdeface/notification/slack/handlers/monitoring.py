"""Monitoring control command handlers for Slack."""

from typing import Any

from ....cli.types import CLIContext, CommandResult
from ....storage import get_storage_manager
from ....utils.logging import get_structured_logger
from ..permissions import Permission
from .base import AsyncCommandMixin, BaseSlackHandler

logger = get_structured_logger(__name__)


class MonitoringHandler(BaseSlackHandler, AsyncCommandMixin):
    """Handles monitoring control commands from Slack."""

    def get_required_permissions(self, subcommands: list[str]) -> list[Permission]:
        """Get required permissions for monitoring commands."""
        if len(subcommands) < 2:
            return [Permission.VIEW_MONITORING]

        command = subcommands[1]

        permission_map = {
            "start": [Permission.CONTROL_MONITORING],
            "stop": [Permission.CONTROL_MONITORING],
            "pause": [Permission.CONTROL_MONITORING],
            "resume": [Permission.CONTROL_MONITORING],
            "check": [Permission.VIEW_MONITORING],
        }

        return permission_map.get(command, [Permission.VIEW_MONITORING])

    async def _execute_command(
        self,
        subcommands: list[str],
        args: dict[str, Any],
        flags: dict[str, Any],
        global_flags: dict[str, Any],
        user_id: str,
    ) -> CommandResult:
        """Execute monitoring command logic."""
        if len(subcommands) < 2:
            # Check if we have an unknown command in args
            if 0 in args:
                unknown_cmd = str(args[0])
                if unknown_cmd not in ["start", "stop", "pause", "resume", "check"]:
                    return CommandResult(
                        success=False,
                        message="Unknown monitoring command",
                        exit_code=1,
                    )
            return CommandResult(
                success=False,
                message="Monitoring command is required (start, stop, pause, resume, check)",
                exit_code=1,
            )

        command = subcommands[1]
        cli_context = self.create_cli_context(global_flags, user_id)

        try:
            if command == "start":
                return await self._handle_start(args, flags, cli_context)
            elif command == "stop":
                return await self._handle_stop(args, flags, cli_context)
            elif command == "pause":
                return await self._handle_pause(args, flags, cli_context)
            elif command == "resume":
                return await self._handle_resume(args, flags, cli_context)
            elif command == "check":
                return await self._handle_check(args, flags, cli_context)
            else:
                return CommandResult(
                    success=False,
                    message="Unknown monitoring command",
                    exit_code=1,
                )
        except Exception as e:
            logger.error(
                "Monitoring command execution failed", command=command, error=str(e)
            )
            return CommandResult(
                success=False, message="Command failed", exit_code=1
            )

    async def _handle_start(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle monitoring start command."""
        website_id = None
        if args:
            website_id = str(args[0])

        try:
            # Use lazy import to avoid circular dependency
            from ....scheduler.orchestrator import get_scheduling_orchestrator
            orchestrator = await get_scheduling_orchestrator()
            storage = await get_storage_manager()

            if website_id:
                # Start monitoring for specific website
                website = await storage.get_website(website_id)
                if not website:
                    return CommandResult(
                        success=False,
                        message=f"Website not found: {website_id}",
                        exit_code=1,
                    )

                if website.is_active:
                    return CommandResult(
                        success=False,
                        message=f"Monitoring already active for: {website.name}",
                        exit_code=1,
                    )

                # Activate website and start monitoring
                await storage.update_website(website_id, {"is_active": True})
                execution_id = await orchestrator.schedule_website_monitoring(
                    website_id
                )

                return CommandResult(
                    success=True,
                    message=f"Started monitoring for: {website.name}",
                    data={
                        "website_id": website_id,
                        "website_name": website.name,
                        "execution_id": execution_id,
                    },
                )
            else:
                # Start monitoring for all inactive websites
                websites = await storage.list_websites()
                inactive_websites = [w for w in websites if not w.is_active]

                if not inactive_websites:
                    return CommandResult(
                        success=True,
                        message="All websites are already being monitored",
                        data={"started_count": 0},
                    )

                started_count = 0
                results = []

                for website in inactive_websites:
                    try:
                        await storage.update_website(website.id, {"is_active": True})
                        execution_id = await orchestrator.schedule_website_monitoring(
                            website.id
                        )
                        started_count += 1
                        results.append(
                            {
                                "website_id": website.id,
                                "website_name": website.name,
                                "execution_id": execution_id,
                                "success": True,
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "website_id": website.id,
                                "website_name": website.name,
                                "error": str(e),
                                "success": False,
                            }
                        )

                return CommandResult(
                    success=True,
                    message=f"Started monitoring for {started_count} websites",
                    data={
                        "started_count": started_count,
                        "total_websites": len(inactive_websites),
                        "results": results,
                    },
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to start monitoring: {str(e)}",
                exit_code=1,
            )

    async def _handle_stop(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle monitoring stop command."""
        website_id = None
        if args:
            website_id = str(args[0])

        try:
            # Use lazy import to avoid circular dependency
            from ....scheduler.orchestrator import get_scheduling_orchestrator
            orchestrator = await get_scheduling_orchestrator()
            storage = await get_storage_manager()

            if website_id:
                # Stop monitoring for specific website
                website = await storage.get_website(website_id)
                if not website:
                    return CommandResult(
                        success=False,
                        message=f"Website not found: {website_id}",
                        exit_code=1,
                    )

                if not website.is_active:
                    return CommandResult(
                        success=False,
                        message=f"Monitoring already stopped for: {website.name}",
                        exit_code=1,
                    )

                # Deactivate website and stop monitoring
                await storage.update_website(website_id, {"is_active": False})
                await orchestrator.unschedule_website_monitoring(website_id)

                return CommandResult(
                    success=True,
                    message=f"Stopped monitoring for: {website.name}",
                    data={
                        "website_id": website_id,
                        "website_name": website.name,
                    },
                )
            else:
                # Stop monitoring for all active websites
                websites = await storage.list_websites()
                active_websites = [w for w in websites if w.is_active]

                if not active_websites:
                    return CommandResult(
                        success=True,
                        message="No websites are currently being monitored",
                        data={"stopped_count": 0},
                    )

                stopped_count = 0
                results = []

                for website in active_websites:
                    try:
                        await storage.update_website(website.id, {"is_active": False})
                        await orchestrator.unschedule_website_monitoring(website.id)
                        stopped_count += 1
                        results.append(
                            {
                                "website_id": website.id,
                                "website_name": website.name,
                                "success": True,
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "website_id": website.id,
                                "website_name": website.name,
                                "error": str(e),
                                "success": False,
                            }
                        )

                return CommandResult(
                    success=True,
                    message=f"Stopped monitoring for {stopped_count} websites",
                    data={
                        "stopped_count": stopped_count,
                        "total_websites": len(active_websites),
                        "results": results,
                    },
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to stop monitoring: {str(e)}",
                exit_code=1,
            )

    async def _handle_pause(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle monitoring pause command."""
        if 0 not in args:
            return CommandResult(
                success=False,
                message="Website ID is required for pause command",
                exit_code=1,
            )

        website_id = str(args[0])
        duration = flags.get("duration", 3600)  # Default 1 hour

        try:
            # Use lazy import to avoid circular dependency
            from ....scheduler.orchestrator import get_scheduling_orchestrator
            orchestrator = await get_scheduling_orchestrator()
            storage = await get_storage_manager()

            website = await storage.get_website(website_id)
            if not website:
                return CommandResult(
                    success=False,
                    message=f"Website not found: {website_id}",
                    exit_code=1,
                )

            if not website.is_active:
                return CommandResult(
                    success=False,
                    message=f"Monitoring not active for: {website.name}",
                    exit_code=1,
                )

            # Pause monitoring for specified duration
            await orchestrator.pause_website_monitoring(website_id, duration)

            return CommandResult(
                success=True,
                message=f"Paused monitoring for {website.name} for {duration} seconds",
                data={
                    "website_id": website_id,
                    "website_name": website.name,
                    "pause_duration": duration,
                },
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to pause monitoring: {str(e)}",
                exit_code=1,
            )

    async def _handle_resume(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle monitoring resume command."""
        if 0 not in args:
            return CommandResult(
                success=False,
                message="Website ID is required for resume command",
                exit_code=1,
            )

        website_id = str(args[0])

        try:
            # Use lazy import to avoid circular dependency
            from ....scheduler.orchestrator import get_scheduling_orchestrator
            orchestrator = await get_scheduling_orchestrator()
            storage = await get_storage_manager()

            website = await storage.get_website(website_id)
            if not website:
                return CommandResult(
                    success=False,
                    message=f"Website not found: {website_id}",
                    exit_code=1,
                )

            # Resume monitoring
            await orchestrator.resume_website_monitoring(website_id)

            return CommandResult(
                success=True,
                message=f"Resumed monitoring for: {website.name}",
                data={
                    "website_id": website_id,
                    "website_name": website.name,
                },
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to resume monitoring: {str(e)}",
                exit_code=1,
            )

    async def _handle_check(
        self, args: dict[str, Any], flags: dict[str, Any], ctx: CLIContext
    ) -> CommandResult:
        """Handle monitoring check command."""
        if 0 not in args:
            return CommandResult(
                success=False,
                message="Website ID is required for check command",
                exit_code=1,
            )

        website_id = str(args[0])

        try:
            # Use lazy import to avoid circular dependency
            from ....scheduler.orchestrator import get_scheduling_orchestrator
            orchestrator = await get_scheduling_orchestrator()
            storage = await get_storage_manager()

            website = await storage.get_website(website_id)
            if not website:
                return CommandResult(
                    success=False,
                    message=f"Website not found: {website_id}",
                    exit_code=1,
                )

            # Trigger immediate check
            execution_id = await orchestrator.trigger_immediate_check(website_id)

            return CommandResult(
                success=True,
                message=f"Triggered immediate check for: {website.name}",
                data={
                    "website_id": website_id,
                    "website_name": website.name,
                    "execution_id": execution_id,
                    "check_triggered_at": ctx.timestamp.isoformat(),
                },
            )

        except Exception as e:
            return CommandResult(
                success=False, message="Command failed", exit_code=1
            )


# Export the handler class
__all__ = ["MonitoringHandler"]
