"""Tests for dialog.py — Dialog builder."""

import pytest

from xingintent import Dialog


class TestDialog:
    def test_empty_dialog(self):
        d = Dialog()
        assert len(d) == 0
        assert d.turns == []

    def test_chain_builder(self):
        d = (
            Dialog()
            .human("我想看看摄像头画面。")
            .ai("你想查看哪个房间？")
            .human("卧室。")
        )
        assert len(d) == 3
        assert d.turns[0]["role"] == "user"
        assert d.turns[1]["role"] == "assistant"
        assert d.turns[2]["content"] == "卧室。"

    def test_aliases(self):
        d = Dialog().user("hello").assistant("hi")
        assert d.turns[0]["role"] == "user"
        assert d.turns[1]["role"] == "assistant"

    def test_render_single_turn(self):
        d = Dialog().human("你好")
        rendered = d.render()
        assert rendered == "Human: 你好"

    def test_render_multi_turn(self):
        d = (
            Dialog()
            .human("我想看看摄像头画面。")
            .ai("你想查看哪个房间？")
            .human("卧室。")
        )
        rendered = d.render()
        lines = rendered.split("\n")
        assert len(lines) == 3
        assert lines[0] == "Human: 我想看看摄像头画面。"
        assert lines[1] == "AI: 你想查看哪个房间？"
        assert lines[2] == "Human: 卧室。"

    def test_from_messages(self):
        messages = [
            {"role": "user", "content": "看看门口"},
            {"role": "assistant", "content": "直播还是回放？"},
            {"role": "user", "content": "直播"},
        ]
        d = Dialog.from_messages(messages)
        assert len(d) == 3
        rendered = d.render()
        assert "Human: 看看门口" in rendered
        assert "AI: 直播还是回放？" in rendered

    def test_from_messages_invalid_role(self):
        messages = [{"role": "system", "content": "不支持的role"}]
        with pytest.raises(ValueError, match="Unsupported role"):
            Dialog.from_messages(messages)

    def test_from_messages_empty(self):
        d = Dialog.from_messages([])
        assert len(d) == 0

    def test_turns_returns_copy(self):
        d = Dialog().human("hi")
        turns = d.turns
        turns.append({"role": "user", "content": "injected"})
        assert len(d) == 1  # Original unchanged

    def test_repr(self):
        d = Dialog().human("hi")
        assert "Dialog" in repr(d)
        assert "1" in repr(d)
