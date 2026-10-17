"""Convert intent definitions to vLLM guided JSON Schema.

When guided_json is enabled, the SDK translates the user's Intent
definitions into a JSON Schema that vLLM uses for constrained decoding,
ensuring the model output always matches the expected structure.
"""

from typing import Any, Dict

from .schema import Schema


def build_guided_schema(schema: Schema) -> Dict[str, Any]:
    """Build a JSON Schema for vLLM guided decoding.

    The generated schema enforces:
    - Output is a JSON array.
    - Each element has a "category" (enum of defined category names).
    - Each element has an "args" array of objects.
    - Arg object keys are the parameter names defined for that category.

    Args:
        schema: The intent schema defining candidate categories and args.

    Returns:
        A JSON Schema dict suitable for vLLM's guided_json parameter.
    """
    all_categories = schema.get_categories()

    # Build per-category arg object schemas
    category_arg_schemas: Dict[str, Dict[str, Any]] = {}
    for intent in schema:
        if not intent.args:
            continue
        properties = {}
        for arg in intent.args:
            properties[arg.name] = {"type": "string"}
        category_arg_schemas[intent.category] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

    # Build the args item schema: union of all possible arg object shapes
    # vLLM supports anyOf for this purpose
    if len(category_arg_schemas) == 1:
        args_item_schema = list(category_arg_schemas.values())[0]
    elif len(category_arg_schemas) > 1:
        args_item_schema = {
            "anyOf": list(category_arg_schemas.values()) + [{"type": "object", "additionalProperties": False}]
        }
    else:
        args_item_schema = {
            "type": "object",
            "additionalProperties": False,
        }

    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": all_categories,
                },
                "args": {
                    "type": "array",
                    "items": args_item_schema,
                },
            },
            "required": ["category", "args"],
            "additionalProperties": False,
        },
    }
