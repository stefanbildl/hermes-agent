"""Telegram private-topic ingress must not infer a topic from a reply anchor or last-active chat."""

from types import SimpleNamespace

from gateway.config import Platform, PlatformConfig
from gateway.platforms.event import MessageType
from gateway.session import SessionSource, build_session_key
from hermes_state import SessionDB
from plugins.platforms.telegram.adapter import TelegramAdapter
from gateway.run import GatewayRunner


def _message(thread_id, *, topic, reply_thread=None, reply_topic=False):
    reply = (SimpleNamespace(message_id=939, message_thread_id=reply_thread,
                             is_topic_message=reply_topic, text="", caption=None) if reply_thread else None)
    return SimpleNamespace(
        text="INBOUND THREAD TEST", caption=None, message_id=966, date=None,
        chat=SimpleNamespace(id=8533576994, type="private", is_forum=True,
                             title=None, full_name="Stefan"),
        from_user=SimpleNamespace(id=8533576994, full_name="Stefan", is_bot=False),
        message_thread_id=thread_id, is_topic_message=topic, reply_to_message=reply,
    )


def _adapter():
    adapter = object.__new__(TelegramAdapter)
    adapter.platform = Platform.TELEGRAM
    adapter._dm_topics = {}
    adapter._dm_topics_config = []
    adapter.config = PlatformConfig(enabled=True, token="***", extra={})
    return adapter


def test_private_topic_keeps_explicit_thread_despite_cross_topic_reply():
    adapter = _adapter()
    msg = _message(2316, topic=True, reply_thread=2304, reply_topic=True)
    event = adapter._build_message_event(msg, MessageType.TEXT)
    assert event.source.thread_id == "2316"
    assert build_session_key(event.source).endswith(":2316")


def test_private_reply_anchor_without_topic_does_not_invent_a_thread():
    adapter = _adapter()
    msg = _message(939, topic=False, reply_thread=2304, reply_topic=True)
    event = adapter._build_message_event(msg, MessageType.TEXT)
    assert event.source.thread_id is None


def test_general_dm_message_does_not_recover_to_latest_topic(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    db.enable_telegram_topic_mode(chat_id="8533576994", user_id="8533576994")
    for thread in ("2304", "2316"):
        db.create_session(session_id=f"sess-{thread}", source="telegram", user_id="8533576994")
        db.bind_telegram_topic(chat_id="8533576994", thread_id=thread,
                               user_id="8533576994", session_key=f"session:{thread}",
                               session_id=f"sess-{thread}")
    runner = object.__new__(GatewayRunner)
    runner._session_db = db
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="8533576994",
                           user_id="8533576994", chat_type="dm", thread_id=None)
    assert runner._recover_telegram_topic_thread_id(source) is None
