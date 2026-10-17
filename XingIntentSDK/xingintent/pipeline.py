"""Post-processing pipeline for model responses.

Provides pluggable processors that run after the raw model output
is parsed. Processors are referenced by name string, keeping the
public API clean.
"""

import json
import re
from typing import Any, Dict, List

from .exceptions import ParseError, ValidationError
from .schema import Schema


def strip_markdown(content: str) -> str:
    """Remove markdown code fences and leading/trailing whitespace.

    Models sometimes wrap JSON output in ```json ... ``` blocks.
    This processor strips those wrappers before JSON parsing.
    """
    text = content.strip()
    # Remove leading ```json or ``` and trailing ```
    if text.startswith("```"):
        # Remove opening fence (possibly with language tag)
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return text


def parse_json(content: str) -> List[Dict[str, Any]]:
    """Parse the model output content into a list of prediction dicts.

    Tries direct JSON parse first, then falls back to extracting
    the first JSON array found in the text.

    Raises:
        ParseError: If the content cannot be parsed as valid JSON.
    """
    text = content.strip()
    if not text:
        raise ParseError("Empty response content", raw_content=content)

    # Direct parse
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try stripping markdown wrappers and retry
        cleaned = strip_markdown(text)
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try extracting JSON array with regex
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                except json.JSONDecodeError:
                    raise ParseError(
                        "Failed to parse model output as JSON",
                        raw_content=content,
                    )
            else:
                raise ParseError(
                    "No JSON array found in model output",
                    raw_content=content,
                )

    if isinstance(result, dict):
        # Single object — wrap in a list
        result = [result]
    elif not isinstance(result, list):
        raise ParseError(
            f"Expected JSON array, got {type(result).__name__}",
            raw_content=content,
        )

    return result


def arg_validate(
    predictions: List[Dict[str, Any]],
    schema: Schema,
) -> List[Dict[str, Any]]:
    """Validate that predicted categories and arg names exist in the schema.

    Removes invalid arg names silently, and raises ValidationError for
    unknown categories (unless it's the fallback category).

    Args:
        predictions: Parsed prediction dicts from the model.
        schema: The intent schema used for this prediction.

    Returns:
        Cleaned predictions with only valid arg names.

    Raises:
        ValidationError: If a predicted category is not in the schema.
    """
    valid_categories = set(schema.get_categories())
    category_arg_map = {
        intent.category: {arg.name for arg in intent.args}
        for intent in schema
    }

    result = []
    for pred in predictions:
        category = pred.get("category", "")
        if category not in valid_categories:
            raise ValidationError(
                f"Predicted category '{category}' not in schema",
                category=category,
            )

        valid_arg_names = category_arg_map.get(category, set())
        cleaned_args = []
        for arg_obj in pred.get("args", []):
            filtered = {k: v for k, v in arg_obj.items() if k in valid_arg_names}
            if filtered:
                cleaned_args.append(filtered)

        result.append({"category": category, "args": cleaned_args})

    return result


def get_postprocessor(name: str):
    """Look up a postprocessor function by name.

    Args:
        name: Processor name. One of: "strip_markdown", "arg_validate".

    Returns:
        The callable processor function.

    Raises:
        ValueError: If the processor name is unknown.
    """
    processors = {
        "strip_markdown": strip_markdown,
        "arg_validate": arg_validate,
    }
    if name not in processors:
        raise ValueError(
            f"Unknown postprocessor: '{name}'. "
            f"Available: {list(processors.keys())}"
        )
    return processors[name]
