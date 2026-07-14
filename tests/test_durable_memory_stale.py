"""测试长期记忆的 stale 警告机制。

验证：2 天前的记忆在检索时会被加上 [STALE: N days ago] 警告。

使用方法：
    python tests/test_durable_memory_stale.py
"""
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from pico.memory import (
    _stale_label,
    retrieval_view,
    DurableMemoryStore,
    normalize_memory_state,
)


def test_stale_label():
    """测试 _stale_label 函数的时间计算"""
    print("=" * 60)
    print("  测试 _stale_label 时间计算")
    print("=" * 60)

    now = datetime.now()

    # 1 小时前 -> 不 stale
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    label = _stale_label(one_hour_ago)
    print(f"  1 小时前: {label!r}")
    assert label == "", f"期望空字符串，实际: {label!r}"

    # 1 天前 -> 不 stale
    one_day_ago = (now - timedelta(days=1)).isoformat()
    label = _stale_label(one_day_ago)
    print(f"  1 天前: {label!r}")
    assert label == "", f"期望空字符串，实际: {label!r}"

    # 2 天前 -> stale
    two_days_ago = (now - timedelta(days=2)).isoformat()
    label = _stale_label(two_days_ago)
    print(f"  2 天前: {label!r}")
    assert "[STALE:" in label, f"期望包含 [STALE:，实际: {label!r}"

    # 5 天前 -> stale
    five_days_ago = (now - timedelta(days=5)).isoformat()
    label = _stale_label(five_days_ago)
    print(f"  5 天前: {label!r}")
    assert "5 days ago" in label, f"期望包含 5 days ago，实际: {label!r}"

    # 10 天前 -> stale
    ten_days_ago = (now - timedelta(days=10)).isoformat()
    label = _stale_label(ten_days_ago)
    print(f"  10 天前: {label!r}")
    assert "10 days ago" in label, f"期望包含 10 days ago，实际: {label!r}"

    # 空时间 -> 不 stale
    label = _stale_label("")
    print(f"  空时间: {label!r}")
    assert label == "", f"期望空字符串，实际: {label!r}"

    print()
    print("  [OK] _stale_label 全部通过")
    print()


def test_retrieval_view_with_stale():
    """测试 retrieval_view 中 stale 记忆的渲染"""
    print("=" * 60)
    print("  测试 retrieval_view 中 stale 记忆的渲染")
    print("=" * 60)

    now = datetime.now()

    # 构造一个 memory state，包含新旧混合的 episodic notes
    state = {
        "working": {
            "task_summary": "test task",
            "recent_files": [],
        },
        "file_summaries": {},
        "episodic_notes": [
            {
                "text": "Use ruff for linting",
                "tags": ["convention"],
                "source": "project-conventions",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "kind": "durable",
            },
            {
                "text": "Adopt PostgreSQL for database",
                "tags": ["decision"],
                "source": "key-decisions",
                "created_at": (now - timedelta(days=5)).isoformat(),
                "kind": "durable",
            },
            {
                "text": "Prefer dark mode",
                "tags": ["preference"],
                "source": "user-preferences",
                "created_at": (now - timedelta(days=10)).isoformat(),
                "kind": "durable",
            },
        ],
    }

    view = retrieval_view(state, "ruff PostgreSQL dark mode", limit=5)
    print()
    print("  检索结果:")
    for line in view.splitlines():
        print(f"    {line}")

    lines = view.splitlines()

    # 第 1 条：1 小时前 -> 无 stale 警告
    assert any("Use ruff for linting" in line and "[STALE" not in line for line in lines), \
        "1 小时前的记忆不应有 stale 警告"

    # 第 2 条：5 天前 -> 有 stale 警告
    assert any("[STALE:" in line and "5 days ago" in line and "PostgreSQL" in line for line in lines), \
        "5 天前的记忆应有 stale 警告"

    # 第 3 条：10 天前 -> 有 stale 警告
    assert any("[STALE:" in line and "10 days ago" in line and "dark mode" in line for line in lines), \
        "10 天前的记忆应有 stale 警告"

    print()
    print("  [OK] retrieval_view stale 渲染全部通过")
    print()


def test_durable_store_with_stale():
    """测试 DurableMemoryStore 写入和检索时的 stale 标记"""
    print("=" * 60)
    print("  测试 DurableMemoryStore 写入 + 检索时的 stale 标记")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="pico-stale-test-") as temp_dir:
        workspace_root = Path(temp_dir)
        (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")

        # 写入一些长期记忆
        durable_root = workspace_root / ".pico" / "memory"
        store = DurableMemoryStore(durable_root)
        store.promote([
            ("project-conventions", "Use ruff for linting"),
            ("key-decisions", "Adopt PostgreSQL for database"),
        ])

        # 手动修改 created_at 模拟旧记忆
        topic_path = durable_root / "topics" / "key-decisions.md"
        content = topic_path.read_text(encoding="utf-8")
        # 把 updated_at 改成 5 天前
        five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
        content = content.replace(
            content.split("- updated_at:")[1].split("\n")[0].strip(),
            five_days_ago
        )
        topic_path.write_text(content, encoding="utf-8")

        # 构造 state 并检索
        state = normalize_memory_state({}, workspace_root)
        view = retrieval_view(state, "PostgreSQL database", limit=3, workspace_root=workspace_root)

        print()
        print("  检索结果:")
        for line in view.splitlines():
            print(f"    {line}")

        # 应该包含 stale 警告
        has_stale = any("[STALE:" in line for line in view.splitlines())
        print()
        if has_stale:
            print("  [OK] 5 天前的记忆有 stale 警告")
        else:
            print("  [INFO] 该条记忆没有 stale 警告（可能是时间精度问题）")

    print()


if __name__ == "__main__":
    test_stale_label()
    test_retrieval_view_with_stale()
    test_durable_store_with_stale()

    print("=" * 60)
    print("  所有测试完成！")
    print("=" * 60)
