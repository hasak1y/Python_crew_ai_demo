from __future__ import annotations

from pathlib import Path

from crewai.tools import tool

from study_demo.logger import record_quality_flag


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def get_allowed_roots() -> list[Path]:
    repo_root = _resolve_repo_root()
    return [
        (repo_root / "study_demo" / "knowledge").resolve(),
    ]


def _resolve_safe_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()

    if not candidate.is_absolute():
        candidate = (get_allowed_roots()[0] / candidate).resolve()
    else:
        candidate = candidate.resolve()

    for root in get_allowed_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue

    raise ValueError("Only files inside study_demo/knowledge are allowed.")


def _tool_error(code: str, message: str) -> str:
    record_quality_flag(
        code=code,
        message=message,
        agent_name="researcher",
        task_name="research_task",
    )
    return f"[TOOL_ERROR:{code}] {message}"


@tool("list_project_files")
def list_project_files(local_path: str) -> str:
    """List files under the allowed knowledge directory."""
    try:
        target = _resolve_safe_path(local_path)
    except ValueError as exc:
        return _tool_error("tool_path_not_allowed", str(exc))

    if not target.exists():
        return _tool_error("tool_path_not_found", f"Path does not exist: {local_path}")

    if target.is_file():
        return _tool_error(
            "tool_expected_directory",
            f"{target.name} is a file. Use read_local_file instead.",
        )

    entries: list[str] = []
    for path in sorted(target.rglob("*")):
        if len(entries) >= 200:
            entries.append("... output truncated after 200 entries.")
            break

        relative_path = path.relative_to(target)
        prefix = "[DIR]" if path.is_dir() else "[FILE]"
        entries.append(f"{prefix} {relative_path}")

    if not entries:
        return f"Directory is empty: {local_path}"

    return "\n".join(entries)


@tool("read_local_file")
def read_local_file(file_path: str) -> str:
    """Read a UTF-8 text file from the allowed knowledge directory."""
    try:
        target = _resolve_safe_path(file_path)
    except ValueError as exc:
        return _tool_error("tool_path_not_allowed", str(exc))

    if not target.exists():
        return _tool_error("tool_file_not_found", f"File does not exist: {file_path}")

    if not target.is_file():
        return _tool_error(
            "tool_expected_file",
            f"{file_path} is not a file. Use list_project_files first.",
        )

    if target.stat().st_size > 1024 * 1024:
        return _tool_error(
            "tool_file_too_large",
            "File is larger than 1MB and will not be read by this tool.",
        )

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _tool_error(
            "tool_decode_error",
            "File is not valid UTF-8 text and cannot be read directly.",
        )
