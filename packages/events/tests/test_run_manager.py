"""Tests for RunManager."""

import pytest


class TestRunManager:
    """Tests for RunManager."""

    @pytest.mark.asyncio
    async def test_create_run(self, run_manager):
        """Should create a new run."""
        from dockrion_events import RunStatus

        run = await run_manager.create_run()

        assert run.run_id is not None
        assert run.status == RunStatus.ACCEPTED
        assert run.created_at is not None

    @pytest.mark.asyncio
    async def test_create_run_with_custom_id(self, run_manager):
        """Should create run with custom ID."""
        run = await run_manager.create_run(run_id="my-custom-run-123")

        assert run.run_id == "my-custom-run-123"

    @pytest.mark.asyncio
    async def test_create_run_duplicate_id_fails(self, run_manager):
        """Should fail on duplicate run ID."""
        from dockrion_common import ValidationError

        await run_manager.create_run(run_id="duplicate-test")

        with pytest.raises(ValidationError, match="already exists"):
            await run_manager.create_run(run_id="duplicate-test")

    @pytest.mark.asyncio
    async def test_create_run_invalid_id_fails(self, run_manager):
        """Should fail on invalid run ID."""
        from dockrion_common import ValidationError

        with pytest.raises(ValidationError):
            await run_manager.create_run(run_id="_invalid")

        with pytest.raises(ValidationError):
            await run_manager.create_run(run_id="a" * 200)  # Too long

    @pytest.mark.asyncio
    async def test_get_run(self, run_manager):
        """Should get run by ID."""
        created = await run_manager.create_run(run_id="get-test")

        run = await run_manager.get_run("get-test")
        assert run is not None
        assert run.run_id == "get-test"

    @pytest.mark.asyncio
    async def test_get_run_not_found(self, run_manager):
        """Should return None for non-existent run."""
        run = await run_manager.get_run("non-existent")
        assert run is None

    @pytest.mark.asyncio
    async def test_start_run(self, run_manager):
        """Should start a run and emit started event."""
        from dockrion_events import RunStatus

        run = await run_manager.create_run(run_id="start-test")
        await run_manager.start_run("start-test")

        run = await run_manager.get_run("start-test")
        assert run.status == RunStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_run_already_started_fails(self, run_manager):
        """Should fail when starting an already started run."""
        from dockrion_common import ValidationError

        await run_manager.create_run(run_id="double-start")
        await run_manager.start_run("double-start")

        with pytest.raises(ValidationError, match="already started"):
            await run_manager.start_run("double-start")

    @pytest.mark.asyncio
    async def test_set_result(self, run_manager):
        """Should set result and mark run completed."""
        from dockrion_events import RunStatus

        await run_manager.create_run(run_id="result-test")
        await run_manager.start_run("result-test")
        await run_manager.set_result(
            "result-test",
            output={"answer": 42},
            latency_seconds=1.5,
        )

        run = await run_manager.get_run("result-test")
        assert run.status == RunStatus.COMPLETED
        assert run.output == {"answer": 42}
        assert run.completed_at is not None

    @pytest.mark.asyncio
    async def test_set_error(self, run_manager):
        """Should set error and mark run failed."""
        from dockrion_events import RunStatus

        await run_manager.create_run(run_id="error-test")
        await run_manager.start_run("error-test")
        await run_manager.set_error(
            "error-test",
            error="Something went wrong",
            code="TEST_ERROR",
            details={"line": 42},
        )

        run = await run_manager.get_run("error-test")
        assert run.status == RunStatus.FAILED
        assert run.error["message"] == "Something went wrong"
        assert run.error["code"] == "TEST_ERROR"

    @pytest.mark.asyncio
    async def test_cancel_run(self, run_manager):
        """Should cancel a running run."""
        from dockrion_events import RunStatus

        await run_manager.create_run(run_id="cancel-test")
        await run_manager.start_run("cancel-test")
        await run_manager.cancel_run("cancel-test", reason="Test cancellation")

        run = await run_manager.get_run("cancel-test")
        assert run.status == RunStatus.CANCELLED
        assert run.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_completed_run_fails(self, run_manager):
        """Should fail when cancelling a completed run."""
        from dockrion_common import ValidationError

        await run_manager.create_run(run_id="cancel-completed")
        await run_manager.start_run("cancel-completed")
        await run_manager.set_result("cancel-completed", output={})

        with pytest.raises(ValidationError, match="already finished"):
            await run_manager.cancel_run("cancel-completed")

    @pytest.mark.asyncio
    async def test_is_terminal(self, run_manager):
        """Should check if run is in terminal state."""
        await run_manager.create_run(run_id="terminal-test")

        # Accepted is not terminal
        assert run_manager.is_terminal("terminal-test") is False

        await run_manager.start_run("terminal-test")
        # Running is not terminal
        assert run_manager.is_terminal("terminal-test") is False

        await run_manager.set_result("terminal-test", output={})
        # Completed is terminal
        assert run_manager.is_terminal("terminal-test") is True

    @pytest.mark.asyncio
    async def test_list_runs(self, run_manager):
        """Should list all runs."""
        await run_manager.create_run(run_id="list-1")
        await run_manager.create_run(run_id="list-2")
        await run_manager.create_run(run_id="list-3")

        runs = run_manager.list_runs()
        assert len(runs) == 3

    @pytest.mark.asyncio
    async def test_list_runs_by_status(self, run_manager):
        """Should filter runs by status."""
        from dockrion_events import RunStatus

        await run_manager.create_run(run_id="status-1")
        await run_manager.create_run(run_id="status-2")
        await run_manager.start_run("status-1")

        accepted_runs = run_manager.list_runs(status=RunStatus.ACCEPTED)
        running_runs = run_manager.list_runs(status=RunStatus.RUNNING)

        assert len(accepted_runs) == 1
        assert len(running_runs) == 1

    @pytest.mark.asyncio
    async def test_cleanup_run(self, run_manager):
        """Should cleanup run from memory."""
        await run_manager.create_run(run_id="cleanup-test")

        run = await run_manager.get_run("cleanup-test")
        assert run is not None

        run_manager.cleanup_run("cleanup-test")

        run = await run_manager.get_run("cleanup-test")
        assert run is None

    @pytest.mark.asyncio
    async def test_get_stats(self, run_manager):
        """Should return run statistics."""
        from dockrion_events import RunStatus

        await run_manager.create_run(run_id="stats-1")
        await run_manager.create_run(run_id="stats-2")
        await run_manager.start_run("stats-1")
        await run_manager.set_result("stats-1", output={})

        stats = run_manager.get_stats()

        assert stats["total"] == 2
        assert stats[RunStatus.COMPLETED.value] == 1
        assert stats[RunStatus.ACCEPTED.value] == 1

    @pytest.mark.asyncio
    async def test_get_context(self, run_manager):
        """Should get StreamContext for a run."""
        await run_manager.create_run(run_id="context-test")

        context = await run_manager.get_context("context-test")
        assert context is not None
        assert context.run_id == "context-test"


class TestRunIdValidation:
    """Tests for run ID validation."""

    def test_valid_run_ids(self):
        """Should accept valid run IDs."""
        from dockrion_events.run_manager import validate_run_id

        # These should not raise
        validate_run_id("abc123")
        validate_run_id("run-123-abc")
        validate_run_id("Run_123")
        validate_run_id("a" * 128)  # Max length

    def test_invalid_run_ids(self):
        """Should reject invalid run IDs."""
        from dockrion_common import ValidationError

        from dockrion_events.run_manager import validate_run_id

        with pytest.raises(ValidationError):
            validate_run_id("")  # Empty

        with pytest.raises(ValidationError):
            validate_run_id("_internal")  # Starts with underscore

        with pytest.raises(ValidationError):
            validate_run_id("a" * 129)  # Too long

        with pytest.raises(ValidationError):
            validate_run_id("run with spaces")  # Invalid characters
