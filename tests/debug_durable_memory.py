"""手动调试长期记忆逻辑的脚本。

使用方法：
    python debug_durable_memory.py
"""
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径（tests/ 的父目录）
sys.path.insert(0, str(Path(__file__).parent.parent))

from pico import MiniAgent, FakeModelClient, SessionStore, WorkspaceContext


def build_workspace(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    # 使用 repo_root_override 强制设置 repo_root 为 tmp_path，避免被 git 检测到父目录
    return WorkspaceContext.build(tmp_path, repo_root_override=tmp_path)


def build_agent(tmp_path, outputs, **kwargs):
    workspace = build_workspace(tmp_path)
    store = SessionStore(tmp_path / ".pico" / "sessions")
    approval_policy = kwargs.pop("approval_policy", "auto")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy=approval_policy,
        **kwargs,
    )


def debug_intent_matching():
    """调试意图关键词匹配"""
    print("=" * 60)
    print("调试 1: 意图关键词匹配")
    print("=" * 60)

    test_messages = [
        "Capture the stable facts into durable memory.",
        "记住这个项目的约定",
        "Save this decision for future reference",
        "How do I fix this bug?",  # 不触发
        "请把下面这些稳定事实记住",
    ]

    from pico.runtime import DURABLE_MEMORY_INTENT_PATTERN, DURABLE_MEMORY_INTENT_ZH_PATTERN

    for msg in test_messages:
        en_match = DURABLE_MEMORY_INTENT_PATTERN.search(msg)
        zh_match = DURABLE_MEMORY_INTENT_ZH_PATTERN.search(msg)
        triggered = bool(en_match or zh_match)
        print(f"  [{triggered}] {msg}")
        if en_match:
            print(f"       -> EN match: '{en_match.group()}'")
        if zh_match:
            print(f"       -> ZH match: '{zh_match.group()}'")
    print()


def debug_line_patterns():
    """调试事实行模式匹配"""
    print("=" * 60)
    print("调试 2: 事实行模式匹配")
    print("=" * 60)

    from pico.runtime import DURABLE_MEMORY_LINE_PATTERNS

    test_lines = [
        "Project convention: Use ruff for linting.",
        "Decision: Prefer sqlite for local storage.",
        "Dependency: Python 3.11 is required.",
        "Preference: Use dark mode.",
        "项目约定：使用 ruff 进行代码检查。",
        "决策：优先使用 sqlite。",
        "Current goal: fix the login bug.",  # 不匹配
        "This is just a normal sentence.",    # 不匹配
    ]

    for line in test_lines:
        matched = False
        for topic, pattern in DURABLE_MEMORY_LINE_PATTERNS:
            match = pattern.match(line)
            if match:
                print(f"  [OK] {line}")
                print(f"       -> topic: {topic}")
                print(f"       -> note: {match.group(1)}")
                matched = True
                break
        if not matched:
            print(f"  [NO] {line}")
    print()


def debug_rejection_logic():
    """调试拒绝检查逻辑"""
    print("=" * 60)
    print("调试 3: 拒绝检查逻辑")
    print("=" * 60)

    # 创建一个临时 agent 来测试拒绝逻辑
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        agent = build_agent(tmp_path, ["<final>done</final>"])

        test_notes = [
            "Use ruff for linting.",                    # 通过
            "API key is sk-live-secret-abc.",           # secret_shaped
            "token: abc123",                             # secret_shaped
            "Current goal: fix the login bug.",         # transient_task_state
            "当前目标: 修复登录问题",                      # transient_task_state
            "stdout: ERROR at line 42",                  # noisy_output
            "a" * 250,                                  # noisy_output (太长)
        ]

        for note in test_notes:
            reason = agent.reject_durable_reason(note)
            status = "REJECT" if reason else "PASS"
            print(f"  [{status}] {note[:50]}...")
            if reason:
                print(f"       -> reason: {reason}")
    print()


def debug_full_flow():
    """调试完整流程"""
    print("=" * 60)
    print("调试 4: 完整流程")
    print("=" * 60)

    # 使用固定目录，方便查看生成的文件
    debug_dir = Path(__file__).parent.parent / "debug_output"
    if debug_dir.exists():
        import shutil
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True)
    tmp_path = debug_dir

    # 模拟模型输出
    model_output = (
        "<final>Project convention: Use ruff for linting.\n"
        "Project convention: Keep tests deterministic.\n"
        "Decision: Prefer sqlite for local storage.\n"
        "Dependency: Python 3.11 is required.</final>"
    )

    agent = build_agent(tmp_path, [model_output])

    # 触发长期记忆
    user_message = "Capture the stable facts into durable memory."
    print(f"  用户输入: {user_message}")
    print(f"  模型输出:\n{model_output}")
    print()

    # 先提取 <final> 内容（模拟 ask() 方法中的 parse 步骤）
    kind, payload = agent.parse(model_output)
    final_answer = payload if kind == "final" else model_output
    print(f"  提取后的 final_answer (kind={kind}):\n{final_answer}")
    print()

    # 调用提取方法（传入提取后的 final_answer）
    promotions, rejections = agent.extract_durable_promotions(user_message, final_answer)

    print(f"  提取结果:")
    print(f"    promotions ({len(promotions)}):")
    for topic, note in promotions:
        print(f"      - {topic}: {note}")
    print(f"    rejections ({len(rejections)}):")
    for rej in rejections:
        print(f"      - {rej}")
    print()

    # 运行完整流程
    answer = agent.ask(user_message)
    print(f"  Agent 回答: {answer[:100]}...")
    print()

    # 检查实际写入的长期记忆
    print(f"  实际写入的 promotions:")
    for p in agent.last_durable_promotions:
        print(f"    - {p}")
    print(f"  实际写入的 rejections:")
    for r in agent.last_durable_rejections:
        print(f"    - {r}")
    print()

    # 检查文件
    memory_dir = tmp_path / ".pico" / "memory"
    print(f"  生成的文件:")
    print(f"  输出目录: {tmp_path.absolute()}")
    if memory_dir.exists():
        for f in memory_dir.rglob("*"):
            if f.is_file():
                print(f"  文件: {f.relative_to(tmp_path)}")
                print(f"  内容:")
                for line in f.read_text(encoding="utf-8").splitlines()[:10]:
                    print(f"        {line}")
    else:
        print("    (无文件生成)")
    print()


if __name__ == "__main__":
    # debug_intent_matching()
    # debug_line_patterns()
    # debug_rejection_logic()
    debug_full_flow()

    print("=" * 60)
    print("调试完成！")
    print("=" * 60)
