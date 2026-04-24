"""Regression test for the Windows CancelledError crash when clicking Stop.

Bug symptom (from user's Windows log 2026-04-24):
    await task
    asyncio.exceptions.CancelledError

Root cause: `stop_item` used `except Exception` to swallow the re-raised
CancelledError from the cancelled `_monitor_item` task, but in Python 3.8+
`CancelledError` inherits from `BaseException`, not `Exception`, so it escaped
the handler and bubbled up to ASGI as a 500.

This test makes `stop_item` cancel a task that re-raises `CancelledError`
(mirroring what `_monitor_item` does) and asserts the call returns normally.
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def _cancelling_worker():
    try:
        await asyncio.sleep(3600)
    except asyncio.CancelledError:
        # Mirror the real _monitor_item behaviour: re-raise.
        raise


@pytest.mark.asyncio
async def test_stop_item_does_not_leak_cancelled_error(monkeypatch):
    """Calling stop_item on a running worker must return {ok: True}, never
    propagate CancelledError to the HTTP layer."""
    from engine import MonitorEngine
    import db

    # Stub the DB write so we don't touch SQLite in the unit test.
    async def _noop(*_a, **_kw):
        return None
    monkeypatch.setattr(db, "set_watch_status", _noop)

    eng = MonitorEngine()
    task = asyncio.create_task(_cancelling_worker())
    eng.workers["test-watch-id"] = task
    # Give it a tick to actually enter the sleep.
    await asyncio.sleep(0)

    result = await eng.stop_item("test-watch-id")
    assert result == {"ok": True}
    assert "test-watch-id" not in eng.workers


@pytest.mark.asyncio
async def test_stop_all_drains_drop_tasks(monkeypatch):
    """Same contract for stop_all — cancelled drop tasks must not crash the caller."""
    from engine import MonitorEngine
    import db

    async def _noop(*_a, **_kw):
        return None
    monkeypatch.setattr(db, "set_watch_status", _noop)

    eng = MonitorEngine()
    t = asyncio.create_task(_cancelling_worker())
    eng.drop_tasks["drop-1"] = t
    await asyncio.sleep(0)

    result = await eng.stop_all()
    assert result["ok"] is True
    assert "drop-1" not in eng.drop_tasks
