"""Declarative intent and argument definitions."""

import json
import os
from typing import Any, Dict, List, Optional, Union, Iterator

from .exceptions import SchemaError


class Arg:
    """Defines a single extractable parameter for an intent.

    Args:
        name: Parameter name (must match schema key in model output).
        description: Human-readable description of what this parameter captures.
    """

    def __init__(self, name: str, description: str):
        if not name:
            raise SchemaError("Arg name cannot be empty")
        self.name = name
        self.description = description

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}

    def __repr__(self) -> str:
        return f"Arg(name={self.name!r}, description={self.description!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Arg) and self.name == other.name and self.description == other.description


class Intent:
    """Defines a single intent category with its parameters.

    Args:
        category: Intent name (used in model output).
        description: Meaning, judgment conditions, and boundaries of this intent.
        args: List of extractable parameters. Empty list if no params.
    """

    def __init__(
        self,
        category: str,
        description: str,
        args: Optional[List[Arg]] = None,
    ):
        if not category:
            raise SchemaError("Intent category cannot be empty")
        self.category = category
        self.description = description
        self.args = args or []
        self.is_fallback: bool = False

    @staticmethod
    def fallback(category: str = "其他意图") -> "Intent":
        """Quick constructor for a fallback / catch-all intent."""
        intent = Intent(
            category=category,
            description="用户输入无法匹配上述类别。",
            args=[],
        )
        intent.is_fallback = True
        return intent

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Intent":
        """Build an Intent from a dict (e.g. parsed from JSON)."""
        if "category" not in d:
            raise SchemaError("Intent dict must contain 'category' key")
        args = [
            Arg(name=arg_data["name"], description=arg_data.get("description", ""))
            for arg_data in d.get("args", [])
        ]
        return Intent(
            category=d["category"],
            description=d.get("category_description", ""),
            args=args,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "category_description": self.description,
            "args": [a.to_dict() for a in self.args],
        }

    def __repr__(self) -> str:
        return f"Intent(category={self.category!r}, args={self.args})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Intent) and self.to_dict() == other.to_dict()


class Schema:
    """Collection of intent definitions passed to the model.

    Args:
        intents: List of Intent objects defining all candidate categories.
    """

    def __init__(self, intents: List[Intent]):
        if not intents:
            raise SchemaError("Schema must contain at least one intent")
        self.intents = list(intents)

    @staticmethod
    def from_json(source: Union[str, list]) -> "Schema":
        """Load schema from a JSON string, file path, or parsed list.

        Args:
            source: JSON string, file path, or a parsed list.
        """
        if isinstance(source, list):
            data = source
        elif isinstance(source, str) and not os.path.exists(source):
            data = json.loads(source)
        else:
            with open(source, "r", encoding="utf-8") as f:
                data = json.load(f)

        intents = [Intent.from_dict(item) for item in data]
        return Schema(intents)

    def to_list(self) -> List[Dict[str, Any]]:
        return [intent.to_dict() for intent in self.intents]

    def to_json(self) -> str:
        """Serialize schema to a compact JSON string (no indentation)."""
        return json.dumps(self.to_list(), ensure_ascii=False)

    def get_categories(self) -> List[str]:
        return [intent.category for intent in self.intents]

    def get_arg_names(self, category: str) -> List[str]:
        for intent in self.intents:
            if intent.category == category:
                return [arg.name for arg in intent.args]
        return []

    def find_intent(self, category: str) -> Optional[Intent]:
        for intent in self.intents:
            if intent.category == category:
                return intent
        return None

    def __iter__(self) -> Iterator[Intent]:
        return iter(self.intents)

    def __len__(self) -> int:
        return len(self.intents)

    def __getitem__(self, index: int) -> Intent:
        return self.intents[index]

    def __repr__(self) -> str:
        return f"Schema(intents={self.intents})"
