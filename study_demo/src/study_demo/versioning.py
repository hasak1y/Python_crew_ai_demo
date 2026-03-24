from __future__ import annotations

import os


# Workflow-level versioning
WORKFLOW_VERSION = "workflow-v1.1.0"
PROMPT_VERSION = "prompt-v1.1.0"
AGENTS_CONFIG_VERSION = "agents-v1.1.0"
TASKS_CONFIG_VERSION = "tasks-v1.1.0"

# Runtime and implementation versioning
MODEL_CONFIG_VERSION = "model-v1.0.0"
TOOL_VERSION = "tool-v1.1.0"
SCHEMA_VERSION = "schema-v1.1.0"


def get_runtime_versions() -> dict[str, str]:
    """Return the version markers needed to correlate behavior changes."""
    return {
        "workflow_version": WORKFLOW_VERSION,
        "prompt_version": PROMPT_VERSION,
        "agents_config_version": AGENTS_CONFIG_VERSION,
        "tasks_config_version": TASKS_CONFIG_VERSION,
        "model_config_version": MODEL_CONFIG_VERSION,
        "tool_version": TOOL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "model_name": os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"),
    }
