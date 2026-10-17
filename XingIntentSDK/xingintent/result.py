"""Rich result objects for model predictions.

Provides attribute-style access to prediction results instead of
requiring users to dig through raw JSON dicts.
"""

from typing import Any, Dict, List, Optional


class IntentResult:
    """Represents a single predicted intent with its extracted arguments.

    Attributes:
        category: The predicted intent category name.
        args: List of argument dicts, each mapping param names to values.
            For single-instance params, access via :attr:`args_flat` for convenience.
    """

    def __init__(self, category: str, args: Optional[List[Dict[str, str]]] = None):
        self.category = category
        self.args = args or []

    @property
    def args_flat(self) -> Dict[str, str]:
        """Flatten all arg dicts into a single dict.

        When the model returns multiple arg instances, later values
        for the same key take precedence.
        """
        merged = {}
        for arg_obj in self.args:
            merged.update(arg_obj)
        return merged

    @property
    def is_empty_args(self) -> bool:
        """True if this intent has no extracted arguments."""
        return len(self.args) == 0

    def get(self, key: str, default: str = "") -> str:
        """Get a single argument value by name from the flattened args."""
        return self.args_flat.get(key, default)

    def __getitem__(self, key: str) -> str:
        """Dict-style access to flattened args: ``result["时间"]``."""
        return self.args_flat[key]

    def __contains__(self, key: str) -> bool:
        return key in self.args_flat

    def __repr__(self) -> str:
        return f"IntentResult(category={self.category!r}, args={self.args_flat!r})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, IntentResult)
            and self.category == other.category
            and self.args == other.args
        )


class PredictResult:
    """Top-level result object returned by :meth:`IntentClient.predict`.

    For single-label tasks, use :attr:`category` and :attr:`args` directly.
    For multi-label tasks, iterate :attr:`intents`.

    Attributes:
        intents: List of all predicted IntentResult objects.
        raw: The raw parsed JSON list from the model output.
    """

    def __init__(self, predictions: List[Dict[str, Any]], fallback_category: str = ""):
        self.raw = predictions
        self.intents: List[IntentResult] = []
        self._fallback_category = fallback_category

        for pred in predictions:
            category = pred.get("category", "")
            args = pred.get("args", [])
            self.intents.append(IntentResult(category=category, args=args))

    @property
    def category(self) -> str:
        """Primary (first) predicted category. Empty string if no predictions."""
        if self.intents:
            return self.intents[0].category
        return ""

    @property
    def args(self) -> Dict[str, str]:
        """Flattened args of the primary (first) intent."""
        if self.intents:
            return self.intents[0].args_flat
        return {}

    def get(self, key: str, default: str = "") -> str:
        """Get an arg value from the primary intent."""
        return self.args.get(key, default)

    @property
    def is_fallback(self) -> bool:
        """True if the primary intent matches the fallback / catch-all category."""
        if self._fallback_category and self.intents:
            return self.intents[0].category == self._fallback_category
        return False

    @property
    def is_multi(self) -> bool:
        """True if the model returned more than one intent."""
        return len(self.intents) > 1

    def __getitem__(self, index: int) -> IntentResult:
        return self.intents[index]

    def __iter__(self):
        return iter(self.intents)

    def __len__(self) -> int:
        return len(self.intents)

    def __repr__(self) -> str:
        if self.is_multi:
            return f"PredictResult(intents={self.intents})"
        if self.intents:
            return f"PredictResult(category={self.category!r}, args={self.args!r})"
        return "PredictResult(empty)"
