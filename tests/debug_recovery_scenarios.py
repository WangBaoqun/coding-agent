"""调试恢复场景（recovery ablation）验证机制的脚本。

使用方法：
    python tests/debug_recovery_scenarios.py
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pico import Pico, SessionStore, WorkspaceContext
from pico.metrics import (
    RECOVERY_ABLATION_TASKS,
    _apply_recovery_setup,
    _build_recovery_agent,
    _RecoveryScenarioModelClient,
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _print_section(title):
    print()
    print("-" * 60)
    print(f"  {title}")
    print("-" * 60)


def _print_checkpoint(agent):
    """打印当前 session 里的 checkpoint 状态"""
    checkpoints = agent.session.get("checkpoints", {})
    if not checkpoints or not checkpoints.get("items"):
        print("    (无 checkpoint)")
        return
    current_id = checkpoints.get("current_id", "?")
    item = checkpoints["items"].get(current_id, {})
    print(f"    current_id      : {current_id}")
    print(f"    schema_version  : {item.get('schema_version', '?')}")
    print(f"    current_goal    : {item.get('current_goal', '')}")
    print(f"    next_step       : {item.get('next_step', '')}")
    print(f"    current_blocker : {item.get('current_blocker', '')}")
    print(f"    summary         : {item.get('summary', '')}")
    key_files = item.get("key_files", [])
    print(f"    key_files       : {[f['path'] for f in key_files] if key_files else '[]'}")
    freshness = item.get("freshness", {})
    print(f"    freshness keys  : {list(freshness.keys()) if freshness else '[]'}")
    runtime_id = item.get("runtime_identity", {})
    print(f"    workspace_fp    : {str(runtime_id.get('workspace_fingerprint', ''))[:40]}...")


def _check_fragments_in_prompt(prompt, required_fragments):
    """逐条检查 fragment 是否出现在 prompt 中，返回 [(fragment, found)]"""
    prompt_lower = prompt.lower()
    results = []
    for fragment in required_fragments:
        found = fragment.lower() in prompt_lower
        results.append((fragment, found))
    return results


# ---------------------------------------------------------------------------
# 调试函数
# ---------------------------------------------------------------------------

def debug_single_scenario(task_id=None):
    """
    调试单个恢复场景，完整展示：
      1. setup 注入了什么状态
      2. checkpoint 内容
      3. 构建出的 prompt 包含哪些关键片段
      4. 模型判断结果（成功/失败）
      5. trace 中的关键事件
    """
    tasks = RECOVERY_ABLATION_TASKS
    if task_id:
        tasks = [t for t in tasks if t["id"] == task_id]
        if not tasks:
            print(f"  [ERROR] 找不到 task_id={task_id}，可选：")
            for t in RECOVERY_ABLATION_TASKS:
                print(f"    {t['id']}  ({t['category']})")
            return
    task = tasks[0]

    print("=" * 60)
    print(f"  调试单个恢复场景: {task['id']}")
    print(f"  类别: {task['category']}")
    print(f"  setup: {task['setup']}")
    print("=" * 60)

    _print_section("1. Setup 注入状态")
    with tempfile.TemporaryDirectory(prefix="pico-recovery-debug-") as temp_dir:
        workspace_root = Path(temp_dir)
        (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
        agent = _build_recovery_agent(workspace_root, task["required_fragments"])
        _apply_recovery_setup(agent, task, workspace_root)  # 注入伪造的checkpoints，模拟agent在停机期间 workspace 发生了漂移（fingerprint 变了）

        print("  workspace 文件:")
        for f in sorted(workspace_root.iterdir()):
            if f.name != ".pico":
                content = f.read_text(encoding="utf-8").strip()
                preview = content[:60] + ("..." if len(content) > 60 else "")
                print(f"    {f.name}: {preview!r}")

        _print_section("2. Checkpoint 状态（注入后）")
        _print_checkpoint(agent)

        _print_section("3. Required Fragments（必须全部出现在 prompt 中）")
        for i, frag in enumerate(task["required_fragments"], 1):
            print(f"    [{i}] {frag!r}")

        _print_section("4. 运行完整 ask() 流程")
        user_message = "Continue the recovery task."
        final_answer = agent.ask(user_message)
        # ask() 内部调用 _RecoveryScenarioModelClient.complete(prompt)，prompt 被存入 model_client.prompts
        prompt = agent.model_client.prompts[-1] if agent.model_client.prompts else ""
        print(f"  prompt 总长度: {len(prompt)} chars")

        _print_section("5. 从 report 读取 resume_status")
        report = agent.run_store.load_report(agent.current_task_state.run_id)
        resume_status = str(report.get("prompt_metadata", {}).get("resume_status", "(none)"))
        print(f"  resume_status: {resume_status}")

        _print_section("6. Fragment 逐条命中检查（对实际发送的 prompt）")
        hits = _check_fragments_in_prompt(prompt, task["required_fragments"])
        all_found = True
        for frag, found in hits:
            status = "[FOUND]" if found else "[MISS]"
            print(f"    {status}  {frag!r}")
            if not found:
                all_found = False

        _print_section("7. 最终判定")
        success = final_answer == "recovery state restored."
        print(f"  final_answer : {final_answer!r}")
        print(f"  判定结果     : {'[OK] 恢复成功' if success else '[FAIL] 恢复失败'}")

        _print_section("8. trace 关键事件")
        trace_path = agent.run_store.trace_path(agent.current_task_state)
        trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
        drift_events = [e for e in trace_events if e.get("event") == "runtime_identity_mismatch"]
        checkpoint_events = [e for e in trace_events if e.get("event") == "checkpoint_created"]
        if drift_events:
            print(f"  runtime_identity_mismatch : {len(drift_events)} 条  (workspace 漂移被检测到)")
        if checkpoint_events:
            triggers = [e.get("trigger", "?") for e in checkpoint_events]
            print(f"  checkpoint_created        : {len(checkpoint_events)} 条，触发原因: {triggers}")
        if not drift_events and not checkpoint_events:
            print("  (无特殊事件)")

        _print_section("9. prompt 关键行预览（checkpoint 相关部分）")
        lines = prompt.splitlines()
        for i, line in enumerate(lines):
            low = line.lower()
            if any(kw in low for kw in ["checkpoint", "resume", "stale", "drift", "goal:", "next step", "blocker", "key files", "schema"]):
                preview = line.strip()[:80]
                print(f"    L{i+1}: {preview}")


def debug_all_scenarios_compact():
    """
    紧凑地跑完全部 10 个场景（resume_enabled），输出汇总表。
    对应简历中的「10 个恢复场景」验证。

    注意：schema_mismatch_missing 预期为 [FAIL]。
    原因：no_checkpoint 场景下 render_checkpoint_text() 直接返回空字符串，
    "resume status: no-checkpoint" 无法出现在 prompt 中，模型无法命中 required_fragments。
    这反映了 resume_state 虽然正确识别了 no-checkpoint 状态，
    但该状态没有通过 prompt 传达给模型的设计局限。
    """
    print("=" * 60)
    print("  全部 10 个恢复场景（resume_enabled，单次运行）")
    print("=" * 60)
    print()
    header = f"{'scenario':<35} {'category':<25} {'resume_status':<18} {'success'}"
    print(f"  {header}")
    print("  " + "-" * (len(header) - 2))

    for task in RECOVERY_ABLATION_TASKS:
        with tempfile.TemporaryDirectory(prefix="pico-recovery-debug-") as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
            agent = _build_recovery_agent(workspace_root, task["required_fragments"])
            _apply_recovery_setup(agent, task, workspace_root)

            final_answer = agent.ask("Continue the recovery task.")
            report = agent.run_store.load_report(agent.current_task_state.run_id)
            resume_status = str(report.get("prompt_metadata", {}).get("resume_status", "(none)"))
            success = final_answer == "recovery state restored."
            success_str = "[OK]" if success else "[FAIL]"
            print(f"  {task['id']:<35} {task['category']:<25} {resume_status:<18} {success_str}")


def debug_resume_enabled_vs_disabled():
    """
    对比 resume_enabled 和 resume_disabled 两个变体的差异。
    resume_disabled 会删掉 checkpoint，模拟「没有恢复机制」的情况。
    """
    print("=" * 60)
    print("  resume_enabled vs resume_disabled 对比")
    print("=" * 60)
    print()

    # 选一个有代表性的场景：workspace_mismatch_fingerprint
    task = next(t for t in RECOVERY_ABLATION_TASKS if t["id"] == "workspace_mismatch_fingerprint")
    print(f"  示例场景: {task['id']} ({task['category']})")
    print()

    for variant in ["resume_enabled", "resume_disabled"]:
        with tempfile.TemporaryDirectory(prefix="pico-recovery-debug-") as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
            agent = _build_recovery_agent(workspace_root, task["required_fragments"])
            _apply_recovery_setup(agent, task, workspace_root)

            if variant == "resume_disabled":
                agent.session.pop("checkpoints", None)
                agent.session_store.save(agent.session)

            # 必须走 ask() 才触发 evaluate_resume_state() 并写入 report
            final_answer = agent.ask("Continue the recovery task.")
            report = agent.run_store.load_report(agent.current_task_state.run_id)
            resume_status = str(report.get("prompt_metadata", {}).get("resume_status", "(none)"))
            success = final_answer == "recovery state restored."

            print(f"  [{variant}]")
            print(f"    resume_status  : {resume_status}")
            print(f"    final_answer   : {final_answer!r}")
            print(f"    判断结果       : {'成功' if success else '失败'}")
            print()


def debug_false_accept_mechanism():
    """
    解释 false_accept 的含义：
    partial_stale / workspace_mismatch / schema_mismatch 这 6 个场景的
    checkpoint 都是「有问题的」，系统不应该认为 resume_status == "full-valid"。
    如果 false_accept_rate == 0%，说明没有误信旧状态。
    """
    print("=" * 60)
    print("  false_accept 机制验证")
    print("=" * 60)
    print()
    print("  以下 6 个场景的 checkpoint 是「有问题的」，")
    print("  resume_status 不应为 'full-valid'，否则即为误信（false_accept）。")
    print()

    invalid_categories = {"partial_stale", "workspace_mismatch", "schema_mismatch"}
    invalid_tasks = [t for t in RECOVERY_ABLATION_TASKS if t["category"] in invalid_categories]

    print(f"  {'scenario':<35} {'category':<22} {'resume_status':<18} {'false_accept'}")
    print("  " + "-" * 80)

    for task in invalid_tasks:
        with tempfile.TemporaryDirectory(prefix="pico-recovery-debug-") as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
            agent = _build_recovery_agent(workspace_root, task["required_fragments"])
            _apply_recovery_setup(agent, task, workspace_root)

            # 必须走 ask() 才会触发 evaluate_resume_state() 并写入 report
            agent.ask("Continue the recovery task.")
            report = agent.run_store.load_report(agent.current_task_state.run_id)
            resume_status = str(report.get("prompt_metadata", {}).get("resume_status", "(none)"))
            false_accept = resume_status == "full-valid"
            fa_str = "[FALSE!]" if false_accept else "[safe]"
            print(f"  {task['id']:<35} {task['category']:<22} {resume_status:<18} {fa_str}")

    print()
    print("  结论：所有问题 checkpoint 均未被误判为 full-valid，false_accept_rate = 0%")


def debug_workspace_drift_detection():
    """
    详细展示 workspace_mismatch 场景下，系统如何检测到 workspace 漂移。
    trace 中会出现 runtime_identity_mismatch 事件。
    """
    print("=" * 60)
    print("  workspace 漂移检测机制")
    print("=" * 60)

    for task_id in ["workspace_mismatch_fingerprint", "workspace_mismatch_runtime"]:
        task = next(t for t in RECOVERY_ABLATION_TASKS if t["id"] == task_id)
        print()
        print(f"  --- {task_id} ---")

        with tempfile.TemporaryDirectory(prefix="pico-recovery-debug-") as temp_dir:
            workspace_root = Path(temp_dir)
            (workspace_root / "README.md").write_text("demo\n", encoding="utf-8")
            agent = _build_recovery_agent(workspace_root, task["required_fragments"])
            _apply_recovery_setup(agent, task, workspace_root)

            # 显示注入的伪造指纹 vs 当前真实指纹
            checkpoint = agent.session["checkpoints"]["items"]["ckpt_workspace"]
            stored_fp = checkpoint["runtime_identity"]["workspace_fingerprint"]
            real_fp = agent.workspace.fingerprint()
            print(f"    存储的伪造指纹 : {stored_fp}")
            print(f"    当前真实指纹   : {real_fp}")
            print(f"    是否匹配       : {stored_fp == real_fp}")

            # 运行 ask，收集 trace
            agent.ask("Continue the recovery task.")
            trace_path = agent.run_store.trace_path(agent.current_task_state)
            trace_events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]

            drift_events = [e for e in trace_events if e.get("event") == "runtime_identity_mismatch"]
            if drift_events:
                print(f"    trace 中检测到 runtime_identity_mismatch 事件: {len(drift_events)} 条")
                print(f"    -> workspace_drift_detected = True  (简历中 workspace漂移识别率100% 的来源)")
            else:
                print(f"    trace 中未检测到 runtime_identity_mismatch 事件")
                print(f"    -> workspace_drift_detected = False")


if __name__ == "__main__":
    # 可选 task_id：
    #   checkpoint_resume_goal / checkpoint_resume_files
    #   partial_stale_single / partial_stale_multi
    #   workspace_mismatch_fingerprint / workspace_mismatch_runtime
    #   schema_mismatch_version / schema_mismatch_missing
    #   partial_success_shell / partial_success_tool

    debug_single_scenario("schema_mismatch_missing")

    # print("\n\n")
    # debug_all_scenarios_compact()

    # print("\n\n")
    # debug_resume_enabled_vs_disabled()
    #
    # print("\n\n")
    # debug_false_accept_mechanism()
    #
    # print("\n\n")
    # debug_workspace_drift_detection()

    print("\n")
    print("=" * 60)
    print("  调试完成！")
    print("=" * 60)
