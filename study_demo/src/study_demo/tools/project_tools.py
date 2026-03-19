from pathlib import Path

from crewai.tools import tool


def _resolve_repo_root() -> Path:
    """返回仓库根目录，后续所有白名单目录都基于这里计算。"""
    return Path(__file__).resolve().parents[4]


def get_allowed_roots() -> list[Path]:
    """返回允许访问的根目录列表，默认只开放 knowledge，后续可继续追加白名单。"""
    repo_root = _resolve_repo_root()
    return [
        (repo_root / "study_demo" / "knowledge").resolve(),
    ]


def _resolve_safe_path(raw_path: str) -> Path:
    """把输入路径解析成绝对路径，并限制在白名单目录内。"""
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

    raise ValueError("当前只允许访问 knowledge 目录或白名单目录中的文件。")


@tool("list_project_files")
def list_project_files(local_path: str) -> str:
    """读取 knowledge 目录下指定路径的文件结构，帮助研究员先了解资料布局。"""
    try:
        target = _resolve_safe_path(local_path)
    except ValueError as exc:
        return str(exc)

    if not target.exists():
        return f"路径不存在：{local_path}"

    if target.is_file():
        return f"{target.name} 是文件，不是目录。请改用 read_local_file 读取内容。"

    entries = []
    for path in sorted(target.rglob("*")):
        if len(entries) >= 200:
            entries.append("... 目录内容过多，已截断显示。")
            break

        relative_path = path.relative_to(target)
        prefix = "[DIR]" if path.is_dir() else "[FILE]"
        entries.append(f"{prefix} {relative_path}")

    if not entries:
        return f"目录为空：{local_path}"

    return "\n".join(entries)


@tool("read_local_file")
def read_local_file(file_path: str) -> str:
    """读取 knowledge 目录下指定文本文件的内容，供研究员提取关键信息。"""
    try:
        target = _resolve_safe_path(file_path)
    except ValueError as exc:
        return str(exc)

    if not target.exists():
        return f"文件不存在：{file_path}"

    if not target.is_file():
        return f"{file_path} 不是文件。请改用 list_project_files 查看目录结构。"

    if target.stat().st_size > 1024 * 1024:
        return "文件过大，当前工具只支持读取 1MB 以内的文本文件。"

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "文件不是 UTF-8 文本，当前工具无法直接读取。"
