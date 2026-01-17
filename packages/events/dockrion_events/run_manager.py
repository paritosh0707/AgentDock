"""
Run Manager

Manages the lifecycle and state of agent execution runs.
Provides methods for creating, updating, querying, and cancelling runs.

A Run represents a single execution of an agent with:
    - run_id: Unique identifier
    - status: Current state (accepted, running, completed, failed, cancelled)
    - created_at: Creation timestamp
    - completed_at: Completion timestamp (if finished)
    - output: Result data (if completed)
    - error: Error information (if failed)

Usage:
    from dockrion_events import RunManager, EventBus, InMemoryBackend

    backend = InMemoryBackend()
    bus = EventBus(backend)
    manager = RunManager(bus)

    # Create a run
    run = await manager.create_run()
    print(f"Created: {run.run_id}")

    # Update status
    await manager.update_status(run.run_id, RunStatus.RUNNING)

    # Set result
    await manager.set_result(run.run_id, {"answer": 42})
"""

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from dockrion_common import ValidationError, get_logger
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .bus import EventBus
from .context import StreamContext

logger = get_logger("events.run_manager")


class RunStatus(str, Enum):
    """Status of an agent execution run."""

    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Run(BaseModel):
    """
    Model representing an agent execution run.

    Attributes:
        run_id: Unique run identifier
        status: Current run status
        created_at: When the run was created
        completed_at: When the run finished (if applicable)
        output: Result data (if completed successfully)
        error: Error information (if failed)
        metadata: Additional run metadata
    """

    run_id: str
    status: RunStatus = RunStatus.ACCEPTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("created_at", "completed_at")
    @classmethod
    def serialize_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO8601 format."""
        return v.isoformat() if v else None

    @field_serializer("status")
    @classmethod
    def serialize_status(cls, v: RunStatus) -> str:
        """Serialize status enum to string value."""
        return v.value

    def to_response(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class RunCreateResponse(BaseModel):
    """Response model for run creation."""

    run_id: str
    status: str = "accepted"
    events_url: str
    created_at: datetime

    @field_serializer("created_at")
    @classmethod
    def serialize_datetime(cls, v: datetime) -> str:
        """Serialize datetime to ISO8601 format."""
        return v.isoformat()


# Run ID validation pattern
RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


def validate_run_id(run_id: str) -> None:
    """
    Validate a client-provided run ID.

    Rules:
        - Must be 1-128 characters
        - Allowed characters: alphanumeric, hyphens, underscores
        - Cannot start with underscore (reserved for internal use)

    Args:
        run_id: Run ID to validate

    Raises:
        ValidationError: If run ID is invalid
    """
    if not run_id:
        raise ValidationError("Run ID cannot be empty")

    if len(run_id) > 128:
        raise ValidationError("Run ID must be 128 characters or less")

    if run_id.startswith("_"):
        raise ValidationError("Run ID cannot start with underscore (reserved)")

    if not RUN_ID_PATTERN.match(run_id):
        raise ValidationError(
            "Run ID must contain only alphanumeric characters, hyphens, and underscores, "
            "and must start with an alphanumeric character"
        )


def generate_run_id() -> str:
    """Generate a new UUID-based run ID."""
    return str(uuid.uuid4())


class RunManager:
    """
    Manages the lifecycle of agent execution runs.

    Responsibilities:
        - Create new runs
        - Track run state
        - Update run status
        - Store results/errors
        - Handle cancellation
        - Emit lifecycle events via StreamContext

    The RunManager stores runs in memory by default.
    For production, runs can be stored in Redis (via backend).
    """

    def __init__(
        self,
        event_bus: EventBus,
        allow_client_ids: bool = True,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
    ):
        """
        Initialize the RunManager.

        Args:
            event_bus: EventBus for publishing run events
            allow_client_ids: Whether to accept client-provided run IDs
            agent_name: Default agent name for runs
            framework: Default framework for runs
        """
        self._bus = event_bus
        self._allow_client_ids = allow_client_ids
        self._agent_name = agent_name
        self._framework = framework
        self._runs: Dict[str, Run] = {}
        self._contexts: Dict[str, StreamContext] = {}

        logger.debug(
            "RunManager initialized",
            allow_client_ids=allow_client_ids,
            agent_name=agent_name,
        )

    async def create_run(
        self,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> Run:
        """
        Create a new run.

        Args:
            run_id: Optional client-provided run ID
            metadata: Optional run metadata
            agent_name: Override default agent name
            framework: Override default framework

        Returns:
            Created Run object

        Raises:
            ValidationError: If run_id is invalid or already exists
        """
        # Handle run ID
        if run_id:
            if not self._allow_client_ids:
                raise ValidationError("Client-provided run IDs are not allowed")
            validate_run_id(run_id)
            if run_id in self._runs:
                raise ValidationError(f"Run ID '{run_id}' already exists")
        else:
            run_id = generate_run_id()

        # Create run
        run = Run(
            run_id=run_id,
            status=RunStatus.ACCEPTED,
            metadata=metadata or {},
        )
        self._runs[run_id] = run

        # Create StreamContext for this run
        context = StreamContext(
            run_id=run_id,
            bus=self._bus,
            agent_name=agent_name or self._agent_name,
            framework=framework or self._framework,
        )
        self._contexts[run_id] = context

        logger.info("Run created", run_id=run_id)
        return run

    async def get_run(self, run_id: str) -> Optional[Run]:
        """
        Get a run by ID.

        Args:
            run_id: Run identifier

        Returns:
            Run object if found, None otherwise
        """
        return self._runs.get(run_id)

    async def get_context(
        self,
        run_id: str,
        events_filter: Optional[Any] = None,
    ) -> Optional[StreamContext]:
        """
        Get the StreamContext for a run.

        Args:
            run_id: Run identifier
            events_filter: Optional EventsFilter to set on the context.
                          If provided, will be set/updated on the context
                          to filter which events are emitted.

        Returns:
            StreamContext if run exists, None otherwise

        Note:
            If events_filter is provided, it will be set on the context
            even if the context already has a filter. This allows the
            runtime to apply configuration at execution time.
        """
        context = self._contexts.get(run_id)
        if context is not None and events_filter is not None:
            # Update the filter on the context
            context._events_filter = events_filter
            logger.debug(
                "Events filter applied to context",
                run_id=run_id,
                has_filter=True,
            )
        return context

    async def start_run(self, run_id: str) -> None:
        """
        Mark a run as started/running.

        Emits a 'started' event and updates status to RUNNING.

        Args:
            run_id: Run identifier

        Raises:
            ValidationError: If run not found or already started
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValidationError(f"Run '{run_id}' not found")

        if run.status != RunStatus.ACCEPTED:
            raise ValidationError(f"Run '{run_id}' already started (status: {run.status})")

        # Update status
        run.status = RunStatus.RUNNING

        # Emit started event
        context = self._contexts.get(run_id)
        if context:
            await context.emit_started()

        logger.info("Run started", run_id=run_id)

    async def update_status(self, run_id: str, status: RunStatus) -> None:
        """
        Update run status.

        Args:
            run_id: Run identifier
            status: New status

        Raises:
            ValidationError: If run not found
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValidationError(f"Run '{run_id}' not found")

        run.status = status
        logger.debug("Run status updated", run_id=run_id, status=status.value)

    async def set_result(
        self,
        run_id: str,
        output: Dict[str, Any],
        latency_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Set the successful result of a run.

        Updates status to COMPLETED and emits 'complete' event.

        Args:
            run_id: Run identifier
            output: Result data
            latency_seconds: Total execution time
            metadata: Additional metadata

        Raises:
            ValidationError: If run not found
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValidationError(f"Run '{run_id}' not found")

        # Update run
        run.status = RunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        run.output = output
        if metadata:
            run.metadata.update(metadata)

        # Emit complete event
        context = self._contexts.get(run_id)
        if context:
            await context.emit_complete(
                output=output,
                latency_seconds=latency_seconds,
                metadata=metadata,
            )

        logger.info("Run completed", run_id=run_id, latency_seconds=latency_seconds)

    async def set_error(
        self,
        run_id: str,
        error: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Set the error result of a run.

        Updates status to FAILED and emits 'error' event.

        Args:
            run_id: Run identifier
            error: Error message
            code: Error code
            details: Additional error details

        Raises:
            ValidationError: If run not found
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValidationError(f"Run '{run_id}' not found")

        # Update run
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        run.error = {
            "message": error,
            "code": code,
            "details": details,
        }

        # Emit error event
        context = self._contexts.get(run_id)
        if context:
            await context.emit_error(error=error, code=code, details=details)

        logger.error("Run failed", run_id=run_id, error=error, code=code)

    async def cancel_run(
        self,
        run_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Cancel a running execution.

        Updates status to CANCELLED and emits 'cancelled' event.

        Args:
            run_id: Run identifier
            reason: Reason for cancellation

        Raises:
            ValidationError: If run not found or already finished
        """
        run = self._runs.get(run_id)
        if not run:
            raise ValidationError(f"Run '{run_id}' not found")

        if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            raise ValidationError(f"Run '{run_id}' is already finished (status: {run.status})")

        # Update run
        run.status = RunStatus.CANCELLED
        run.completed_at = datetime.now(timezone.utc)

        # Emit cancelled event
        context = self._contexts.get(run_id)
        if context:
            await context.emit_cancelled(reason=reason)

        logger.info("Run cancelled", run_id=run_id, reason=reason)

    async def emit_heartbeat(self, run_id: str) -> None:
        """
        Emit a heartbeat event for a run.

        Args:
            run_id: Run identifier
        """
        context = self._contexts.get(run_id)
        if context:
            await context.emit_heartbeat()

    def is_terminal(self, run_id: str) -> bool:
        """
        Check if a run is in a terminal state.

        Args:
            run_id: Run identifier

        Returns:
            True if run is completed, failed, or cancelled
        """
        run = self._runs.get(run_id)
        if not run:
            return True  # Non-existent runs are considered terminal

        return run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)

    def list_runs(
        self,
        status: Optional[RunStatus] = None,
        limit: int = 100,
    ) -> list[Run]:
        """
        List runs, optionally filtered by status.

        Args:
            status: Filter by status
            limit: Maximum number of runs to return

        Returns:
            List of Run objects
        """
        runs = list(self._runs.values())

        if status:
            runs = [r for r in runs if r.status == status]

        # Sort by created_at descending
        runs.sort(key=lambda r: r.created_at, reverse=True)

        return runs[:limit]

    def cleanup_run(self, run_id: str) -> None:
        """
        Remove a run from memory.

        Should be called after a run is complete and no longer needed.

        Args:
            run_id: Run identifier
        """
        if run_id in self._runs:
            del self._runs[run_id]
        if run_id in self._contexts:
            del self._contexts[run_id]

        logger.debug("Run cleaned up", run_id=run_id)

    def get_stats(self) -> Dict[str, int]:
        """
        Get run statistics.

        Returns:
            Dict with counts by status
        """
        stats = {status.value: 0 for status in RunStatus}
        for run in self._runs.values():
            stats[run.status.value] += 1
        stats["total"] = len(self._runs)
        return stats
