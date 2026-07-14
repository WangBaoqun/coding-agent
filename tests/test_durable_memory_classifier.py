"""测试基于关键词的长期记忆分类逻辑。

使用方法：
    python tests/test_durable_memory_classifier.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pico.runtime import classify_memory_item


def test_english_classification():
    """测试英文分类"""
    print("=" * 60)
    print("  测试英文分类")
    print("=" * 60)

    test_cases = [
        # (文本, 期望类别)
        ("Use ruff for code linting", "project-conventions"),
        ("The project follows PEP 8 style guide", "project-conventions"),
        ("We decided to adopt PostgreSQL for the database", "key-decisions"),
        ("We will use FastAPI as the web framework", "key-decisions"),
        ("This project requires Python 3.9 or higher", "dependency-facts"),
        ("Install dependencies with pip install -r requirements.txt", "dependency-facts"),
        ("I prefer using dark mode in the editor", "user-preferences"),
        ("The user likes concise commit messages", "user-preferences"),
        ("This is a random sentence without keywords", "unknown"),
    ]

    correct = 0
    for text, expected in test_cases:
        result = classify_memory_item(text)
        status = "[OK]" if result == expected else "[FAIL]"
        if result == expected:
            correct += 1
        print(f"  {status} {text!r}")
        print(f"    期望: {expected}, 实际: {result}")

    print()
    print(f"  正确率: {correct}/{len(test_cases)}")
    print()


def test_chinese_classification():
    """测试中文分类"""
    print("=" * 60)
    print("  测试中文分类")
    print("=" * 60)

    test_cases = [
        # (文本, 期望类别)
        ("项目使用 ruff 做代码检查", "project-conventions"),
        ("代码规范要求使用 4 空格缩进", "project-conventions"),
        ("我们决定采用 PostgreSQL 数据库", "key-decisions"),
        ("确定使用 FastAPI 作为 Web 框架", "key-decisions"),
        ("项目依赖 Python 3.9 或更高版本", "dependency-facts"),
        ("需要安装 requirements.txt 中的依赖", "dependency-facts"),
        ("用户偏好使用深色模式", "user-preferences"),
        ("习惯用简洁的提交信息", "user-preferences"),
        ("这是一句没有关键词的普通句子", "unknown"),
    ]

    correct = 0
    for text, expected in test_cases:
        result = classify_memory_item(text)
        status = "[OK]" if result == expected else "[FAIL]"
        if result == expected:
            correct += 1
        print(f"  {status} {text!r}")
        print(f"    期望: {expected}, 实际: {result}")

    print()
    print(f"  正确率: {correct}/{len(test_cases)}")
    print()


def test_mixed_language():
    """测试中英混合"""
    print("=" * 60)
    print("  测试中英混合")
    print("=" * 60)

    test_cases = [
        ("项目采用 ruff 做 lint", "project-conventions"),
        ("决定使用 PostgreSQL", "key-decisions"),
        ("依赖 package.json 中的版本", "dependency-facts"),
    ]

    for text, expected in test_cases:
        result = classify_memory_item(text)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} {text!r}")
        print(f"    期望: {expected}, 实际: {result}")

    print()


def test_extract_durable_promotions():
    """测试完整的 extract_durable_promotions 流程"""
    print("=" * 60)
    print("  测试 extract_durable_promotions 完整流程")
    print("=" * 60)

    from pico import Pico, WorkspaceContext, SessionStore
    from pico.models import FakeModelClient
    import tempfile

    with tempfile.TemporaryDirectory(prefix="pico-durable-test-") as temp_dir:
        workspace_root = Path(temp_dir)
        (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
        workspace = WorkspaceContext.build(workspace_root)
        store = SessionStore(workspace_root / ".pico" / "sessions")
        agent = Pico(
            model_client=FakeModelClient([]),
            workspace=workspace,
            session_store=store,
            approval_policy="auto",
        )

        # 测试 1：固定前缀格式（向后兼容）
        print("\n  测试 1: 固定前缀格式")
        user_msg = "Remember the project conventions"
        final_answer = """Project convention: Use ruff for linting.
Decision: Adopt pytest for testing."""
        promotions, rejections = agent.extract_durable_promotions(user_msg, final_answer)
        print(f"    用户消息: {user_msg!r}")
        print(f"    模型回答: {final_answer!r}")
        print(f"    提取结果: {promotions}")
        print(f"    拒绝结果: {rejections}")

        # 测试 2：关键词分类（新逻辑）
        print("\n  测试 2: 关键词分类（新逻辑）")
        user_msg = "记住项目的关键决策"
        final_answer = """我们决定采用 PostgreSQL 数据库。
项目使用 ruff 做代码检查。
用户偏好使用深色模式。"""
        promotions, rejections = agent.extract_durable_promotions(user_msg, final_answer)
        print(f"    用户消息: {user_msg!r}")
        print(f"    模型回答: {final_answer!r}")
        print(f"    提取结果: {promotions}")
        print(f"    拒绝结果: {rejections}")

        # 测试 3：混合模式
        print("\n  测试 3: 混合模式（固定前缀 + 关键词）")
        user_msg = "Save the important facts"
        final_answer = """Project convention: Use 4 spaces for indentation.
我们决定采用 FastAPI 框架。
This is a random line without keywords."""
        promotions, rejections = agent.extract_durable_promotions(user_msg, final_answer)
        print(f"    用户消息: {user_msg!r}")
        print(f"    模型回答: {final_answer!r}")
        print(f"    提取结果: {promotions}")
        print(f"    拒绝结果: {rejections}")

        # 测试 4：无记忆意图
        print("\n  测试 4: 无记忆意图（不应提取）")
        user_msg = "帮我修改一下 README"
        final_answer = """我们决定采用 PostgreSQL 数据库。"""
        promotions, rejections = agent.extract_durable_promotions(user_msg, final_answer)
        print(f"    用户消息: {user_msg!r}")
        print(f"    模型回答: {final_answer!r}")
        print(f"    提取结果: {promotions} (应为空)")
        print(f"    拒绝结果: {rejections} (应为空)")


if __name__ == "__main__":
    test_english_classification()
    test_chinese_classification()
    test_mixed_language()
    test_extract_durable_promotions()

    print("=" * 60)
    print("  所有测试完成！")
    print("=" * 60)
