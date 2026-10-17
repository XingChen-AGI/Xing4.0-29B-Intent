"""Multi-turn dialog builder.

Provides a fluent API for constructing multi-turn conversations
that get rendered into the prompt format expected by the model.
"""

from typing import Dict, List, Optional


_ROLE_MAP = {
    "user": "Human",
    "assistant": "AI",
}


class Dialog:
    """Builder for multi-turn conversations.

    Supports both chained calls and construction from standard
    OpenAI-style messages.

    Example::

        dialog = (
            Dialog()
            .human("我想看看摄像头画面。")
            .ai("你想查看哪个房间？")
            .human("卧室。")
        )

    Or from messages::

        dialog = Dialog.from_messages([
            {"role": "user", "content": "我想看看摄像头画面。"},
            {"role": "assistant", "content": "你想查看哪个房间？"},
            {"role": "user", "content": "卧室。"},
        ])
    """

    def __init__(self, turns: Optional[List[Dict[str, str]]] = None):
        self._turns: List[Dict[str, str]] = list(turns) if turns else []

    @staticmethod
    def from_messages(messages: List[Dict[str, str]]) -> "Dialog":
        """Build a Dialog from OpenAI-style messages.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}.
        """
        turns = []
        for msg in messages:
            role = msg["role"]
            if role not in _ROLE_MAP:
                raise ValueError(f"Unsupported role: {role}. Must be 'user' or 'assistant'.")
            turns.append({"role": role, "content": msg["content"]})
        return Dialog(turns)

    def human(self, content: str) -> "Dialog":
        """Add a user turn."""
        self._turns.append({"role": "user", "content": content})
        return self

    def ai(self, content: str) -> "Dialog":
        """Add an assistant turn."""
        self._turns.append({"role": "assistant", "content": content})
        return self

    def user(self, content: str) -> "Dialog":
        """Alias for :meth:`human`."""
        return self.human(content)

    def assistant(self, content: str) -> "Dialog":
        """Alias for :meth:`ai`."""
        return self.ai(content)

    def render(self) -> str:
        """Render the dialog into the prompt format.

        Each turn becomes ``Human: xxx`` or ``AI: xxx``, one per line.
        """
        lines = []
        for turn in self._turns:
            display_name = _ROLE_MAP[turn["role"]]
            lines.append(f"{display_name}: {turn['content']}")
        return "\n".join(lines)

    @property
    def turns(self) -> List[Dict[str, str]]:
        return list(self._turns)

    def __len__(self) -> int:
        return len(self._turns)

    def __repr__(self) -> str:
        return f"Dialog(turns={len(self._turns)})"
