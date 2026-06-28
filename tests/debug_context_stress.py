"""调试上下文压力测试的脚本。

使用方法：
    python tests/debug_context_stress.py
"""
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pico import FakeModelClient, SessionStore, WorkspaceContext, Pico
from pico.metrics import measure_feature_ablation_metrics, run_context_stress_matrix


def debug_single_config():
    """调试单组配置，与 run_context_stress_matrix 使用完全相同的代码路径（包括相同的 tempdir prefix）。

    通过复用 matrix 的构建逻辑，保证 prefix 长度、note 内容、history 内容完全一致，
    输出的数字与 matrix 中对应配置严格相同。
    """
    # 与 run_context_stress_matrix 中循环体完全一致
    history_label, history_count = "medium", 12
    note_label, note_count = "high", 10
    request_label, request_text = "long", "recall the relevant benchmark fact without dropping the latest request details"
    config_id = f"{history_label}-{note_label}-{request_label}"

    print("=" * 60)
    print(f"调试 1: 单组配置 {config_id}（与 matrix 完全一致的代码路径）")
    print("=" * 60)

    # 使用与 matrix 完全相同的 tempdir prefix，确保 prefix 长度一致
    with tempfile.TemporaryDirectory(prefix="pico-context-matrix-") as temp_dir:
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
        # 注入内容：与 matrix 循环体逐字一致
        for index in range(note_count):
            agent.memory.append_note(
                f"matrix-note-{index}-" + ("A" * 180),
                tags=("recall",),
                created_at=f"2026-04-08T10:{index:02d}:00+00:00",
            )
        for index in range(history_count):
            agent.record(
                {
                    "role": "user" if index % 2 == 0 else "assistant",
                    "content": f"matrix-history-{index}-" + ("B" * 220),
                    "created_at": f"2026-04-08T11:{index:02d}:00+00:00",
                }
            )

        metrics = measure_feature_ablation_metrics(agent, request_text)

        print(f"  配置 ID: {config_id}")
        print(f"  history: {history_count} 条，notes: {note_count} 条，request: {request_label}")
        print()

        print("  各变体详情:")
        for variant, data in metrics.items():
            print(f"    {variant}:")
            print(f"      prompt_chars: {data['prompt_chars']}")
            print(f"      memory_chars: {data['memory_chars']}")
            print(f"      history_chars: {data['history_chars']}")
            print(f"      relevant_selected_count: {data['relevant_selected_count']}")
            print(f"      budget_reduction_count: {data['budget_reduction_count']}")
            print(f"      current_request_preserved: {data['current_request_preserved']}")
            print()

        # 计算压缩率（与 matrix 的计算方式完全一致）
        full_chars = metrics["full"]["prompt_chars"]
        raw_chars = metrics["no_context_reduction"]["prompt_chars"]
        if raw_chars > 0:
            ratio = (raw_chars - full_chars) / raw_chars
            print(f"  压缩率: {ratio:.2%}")
            print(f"  原始长度 (raw): {raw_chars} chars")
            print(f"  压缩后长度 (full): {full_chars} chars")
            print(f"  节省: {raw_chars - full_chars} chars")
        print()
        print("  注：上述 raw/full 数字应与 run_context_stress_matrix() 中")
        print(f"  {config_id} 的 avg_raw_prompt_chars / avg_full_prompt_chars 完全一致（repetitions=1 时）。")



def debug_context_stress_matrix(repetitions: int):
    """调试 12 组配置矩阵"""
    print("=" * 60)
    print(f"调试 2: 12 组配置矩阵 (repetitions={repetitions})")
    print("=" * 60)

    results = run_context_stress_matrix(repetitions=repetitions)

    print(f"  配置数量: {results['config_count']}")
    print()

    print("  各配置详情:")
    for config in results["configs"]:
        print(f"    {config['id']}:")
        print(f"      原始长度: {config['avg_raw_prompt_chars']:.0f} chars")
        print(f"      压缩后长度: {config['avg_full_prompt_chars']:.0f} chars")
        print(f"      压缩率: {config['avg_prompt_compression_ratio']:.2%}")
        print(f"      当前请求保留率: {config['current_request_preserved_rate']:.0%}")
        print()

    print("  汇总统计:")
    summary = results["summary"]
    print(f"    平均原始长度: {summary['avg_raw_prompt_chars']:.2f} chars")
    print(f"    平均压缩后长度: {summary['avg_full_prompt_chars']:.2f} chars")
    print(f"    平均压缩率: {summary['avg_prompt_compression_ratio']:.2%}")
    print(f"    最高压缩率: {summary['max_prompt_compression_ratio']:.2%}")
    print(f"    最低压缩率: {summary['min_prompt_compression_ratio']:.2%}")
    print(f"    当前请求保留率: {summary['current_request_preserved_rate']:.2%}")


def debug_budget_reduction_mechanism():
    """调试预算裁剪机制的细节"""
    print("=" * 60)
    print("调试 3: 预算裁剪机制细节")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="pico-budget-debug-") as temp_dir:
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

        # 构造超预算场景
        agent.prefix = "PREFIX " + ("A" * 600)
        agent.memory.render_memory_text = lambda: "MEMORY " + ("B" * 600)
        agent.memory.append_note("note-1 " + ("C" * 220), tags=("keep",), created_at="2026-04-07T10:00:00+00:00")
        agent.memory.append_note("note-2 " + ("D" * 220), tags=("keep",), created_at="2026-04-07T10:01:00+00:00")
        agent.memory.append_note("note-3 " + ("E" * 220), tags=("keep",), created_at="2026-04-07T10:02:00+00:00")

        # 添加旧历史和新历史
        agent.record({"role": "user", "content": "OLD-CONTEXT " + ("D" * 260), "created_at": "2026-04-07T09:59:00+00:00"})
        for minute in range(1, 8):
            role = "assistant" if minute % 2 == 1 else "user"
            content = "RECENT-CONTEXT " + ("E" * 260) if minute == 7 else f"recent-{minute} " + ("E" * 180)
            agent.record({"role": role, "content": content, "created_at": f"2026-04-07T10:0{minute}:00+00:00"})

        from pico.context_manager import ContextManager

        manager = ContextManager(
            agent,
            total_budget=700,
            section_budgets={
                "prefix": 120,
                "memory": 120,
                "relevant_memory": 120,
                "history": 400,
            },
        )

        request = "keep this request verbatim"
        prompt, metadata = manager.build(request)

        print("  预算设置:")
        print(f"    total_budget: {manager.total_budget}")
        print(f"    section_budgets: {manager.section_budgets}")
        print()

        print("  各 section 渲染结果:")
        for section, data in metadata["sections"].items():
            print(f"    {section}:")
            print(f"      raw_chars: {data['raw_chars']}")
            print(f"      budget_chars: {data['budget_chars']}")
            print(f"      rendered_chars: {data['rendered_chars']}")
            print()

        print("  预算裁剪记录:")
        if metadata["budget_reductions"]:
            for entry in metadata["budget_reductions"]:
                print(f"    {entry['section']}: {entry['before_chars']} -> {entry['after_chars']} (overflow: {entry['overflow_chars']})")
        else:
            print("    (无裁剪)")
        print()

        print("  关键验证:")
        print(f"    prompt 长度: {len(prompt)} chars")
        print(f"    是否超预算: {len(prompt) > manager.total_budget}")
        print(f"    当前请求保留: {request in prompt}")
        print(f"    新内容保留: {'RECENT-CONTEXT' in prompt}")
        print(f"    旧内容裁掉: {'OLD-CONTEXT' not in prompt}")


def debug_context_reduction_order():
    """调试裁剪顺序：relevant_memory -> history -> memory -> prefix"""
    print("=" * 60)
    print("调试 4: 裁剪顺序验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="pico-order-debug-") as temp_dir:
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

        # 构造极端超预算场景，强制触发全部 4 级裁剪
        # 各 section 原始内容都远大于其预算，保证渲染后会撑满预算
        agent.prefix = "PREFIX " + ("A" * 500)
        agent.memory.render_memory_text = lambda: "MEMORY " + ("B" * 500)
        # 注入多条 note，让 relevant_memory 有足够内容可裁
        for tag_index in range(3):
            agent.memory.append_note(
                f"note-{tag_index} " + ("C" * 300),
                tags=("recall",),
                created_at=f"2026-04-07T10:{tag_index:02d}:00+00:00",
            )

        for index in range(30):
            agent.record(
                {
                    "role": "user" if index % 2 == 0 else "assistant",
                    "content": f"history-{index} " + ("D" * 200),
                    "created_at": f"2026-04-07T10:{index:02d}:00+00:00",
                }
            )

        from pico.context_manager import ContextManager

        # 各 section 预算均为 100，floor = max(20, 100//4) = 25
        # 设 total_budget=180，使第 3 轮裁完后剩余空间 < floor，强制触发第 4 级
        # 推导：裁完 relevant_memory(25) + history(25) 后，剩余给 memory 的空间
        #   = 180 - prefix(100) - relevant_memory(25) - history(25) - current_request(~50)
        #   = -20 < floor(25)，因此 memory 也被压到 floor，进而触发 prefix 裁剪
        manager = ContextManager(
            agent,
            total_budget=180,
            section_budgets={
                "prefix": 100,
                "memory": 100,
                "relevant_memory": 100,
                "history": 100,
            },
        )

        prompt, metadata = manager.build("this is a deliberately long request to consume budget chars")

        print("  预算设置:")
        print(f"    total_budget: {manager.total_budget}")
        print(f"    section_budgets: {manager.section_budgets}")
        print()

        print("  裁剪顺序记录:")
        reduction_order = [entry["section"] for entry in metadata["budget_reductions"]]
        for i, entry in enumerate(metadata["budget_reductions"]):
            print(f"    第 {i+1} 次裁剪: {entry['section']} ({entry['before_chars']} -> {entry['after_chars']})")
        print()

        print("  预期裁剪顺序: relevant_memory -> history -> memory -> prefix")
        print(f"  实际裁剪顺序: {' -> '.join(reduction_order)}")
        print()

        # 验证顺序
        expected_order = ["relevant_memory", "history", "memory", "prefix"]
        if reduction_order == expected_order:
            print("  ✅ 裁剪顺序完全正确，4 级全部触发")
        elif reduction_order[:len(expected_order)] == expected_order[:len(reduction_order)]:
            print(f"  ✅ 前 {len(reduction_order)} 级裁剪顺序正确（后续未触发）")
        else:
            print("  ❌ 裁剪顺序不符合预期")

        print()
        print("  各 section 最终 floor 值:")
        for section, floor in manager.section_floors.items():
            print(f"    {section}: floor={floor}")


if __name__ == "__main__":
    debug_single_config() # 测试debug_context_stress_matrix的其中一种配置
    print()
    # debug_budget_reduction_mechanism()
    # print()
    # debug_context_reduction_order()
    # print()
    # debug_context_stress_matrix(repetitions=5)

    print()
    print("=" * 60)
    print("调试完成！")
    print("=" * 60)
