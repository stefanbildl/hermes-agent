"""Session-scoped override keys must preserve the actual Telegram topic.

No message from General may inherit the last-active topic's key: a missing
thread id cannot identify which conversation the user intended.
"""

import threading
from unittest.mock import MagicMock

import gateway.run as gateway_run
from gateway.config import Platform
from gateway.session import SessionSource, build_session_key


def _make_runner(recovered_thread_id=None):
    runner = object.__new__(gateway_run.GatewayRunner)
    runner.config = None
    runner.session_store = None
    runner._session_db = None
    runner._session_model_overrides = {}
    runner._session_reasoning_overrides = {}
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    # Stub topic recovery: returns the bound topic id for a lobby message,
    # None otherwise (the real method's contract).
    runner._recover_telegram_topic_thread_id = MagicMock(return_value=recovered_thread_id)
    return runner


def _topic_dm_source(thread_id):
    """A Telegram DM in topic mode. thread_id="" / "1" == General/lobby."""
    return SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="555",
        chat_name="Forum DM",
        chat_type="dm",
        user_id="user-1",
        thread_id=thread_id,
    )


def test_normalize_preserves_lobby_and_explicit_topics():
    """An absent thread cannot identify a topic, even when an older binding exists."""
    runner = _make_runner(recovered_thread_id=None)
    for thread_id in ("", "1", "42"):
        src = _topic_dm_source(thread_id=thread_id)
        normalized = runner._normalize_source_for_session_key(src)
        assert normalized.thread_id == thread_id


