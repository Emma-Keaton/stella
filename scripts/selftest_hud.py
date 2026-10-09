"""
scripts/selftest_hud.py — runtime self-test for the redesign layer.

Covers: design tokens, stylesheet build, PulseDot/NeonDivider, ChatBubble
live streaming (caret), ConversationFeed live-bubble lifecycle, the fixed
"Stella:" log-prefix routing, and responsive chat measure breakpoints.

Run:  py scripts/selftest_hud.py       (system Python has PyQt6)
Exits non-zero on any failure.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(name, cond):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        FAILED.append(name)


def main():
    # ---- design system (no widgets needed for tokens) ----
    from core import hud_theme as H
    check("breakpoint compact", H.breakpoint(600) == "compact")
    check("breakpoint medium", H.breakpoint(900) == "medium")
    check("breakpoint wide", H.breakpoint(1600) == "wide")
    check("measure tightens on wide", H.measure_ratio(1600) < H.measure_ratio(600))
    css = H.build_stylesheet()
    check("stylesheet has scrollbar", "QScrollBar::handle:vertical" in css)
    check("stylesheet has focus ring", "QPushButton:focus" in css)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    check("hud install", H.install(app))
    check("app stylesheet applied", bool(app.styleSheet()))

    from PyQt6.QtCore import QAbstractAnimation
    dot = H.PulseDot()
    check("pulse dot animates", dot._anim.state() == QAbstractAnimation.State.Running)
    div = H.NeonDivider()
    div.resize(120, 1)
    div.repaint()
    check("neon divider constructs", True)

    # ---- ui layer ----
    import ui

    # ChatBubble live streaming
    b = ui.ChatBubble("assistant", "Stella", "", "", parent=None, live=True)
    b.resize(320, 80)
    b.set_live("Hel")
    check("live caret rendered", "\u258b" in b._browser.text())
    b.set_live("Hello world")
    check("live text accumulates", "Hello world" in b._browser.text())
    b.end_live()
    check("caret cleared on end", "\u258b" not in b._browser.text())
    check("caret timer stopped", b._caret_timer is None)

    # The real chat surface: InlineChatWorkspace owns append_log + _feed.
    ws = ui.InlineChatWorkspace()
    ws.resize(700, 500)

    # Stub the persistence store so the self-test writes nothing to user data.
    class _StubStore:
        def record_chat(self, *a, **k):
            return "selftest-conv"

        def get_conversation(self, *a, **k):
            return None

        def ensure_active_conversation(self, *a, **k):
            return "selftest-conv"

        def create_conversation(self, *a, **k):
            return "selftest-conv"

        def search_memories(self, *a, **k):
            return []

        def grouped_conversations(self, *a, **k):
            return []

    ws._store = _StubStore()
    feed = ws._feed
    feed.resize(700, 500)

    # Live bubble lifecycle
    feed.append_live_reply("chunk-1 ")
    feed.append_live_reply("chunk-2")
    check("live bubble exists", feed._live_bubble is not None)
    check("live text accumulated", feed._live_text == "chunk-1 chunk-2")
    feed.end_live_reply("chunk-1 chunk-2")
    check("live bubble retired", feed._live_bubble is None)

    # "Stella:" prefix must now route to an assistant message (rebrand fix)
    before = feed._message_count
    ws.append_log("Stella: fixed prefix reply")
    check("Stella: prefix lands assistant msg", feed._message_count == before + 1)
    # Legacy prefix still works too
    ws.append_log("Stella Evo: legacy prefix reply")
    check("Stella Evo: prefix still lands", feed._message_count == before + 2)

    # Clear resets any stream
    feed.append_live_reply("x")
    feed.clear_messages()
    check("clear resets live bubble", feed._live_bubble is None)

    print("RESULT:", "PASS" if not FAILED else f"FAIL ({len(FAILED)}): {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
