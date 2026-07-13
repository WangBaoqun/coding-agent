from pathlib import Path
from pico.evaluator import run_harness_regression_v2
from pico.metrics import (
    run_context_ablation_v2,
    run_memory_ablation_v2,
    run_recovery_ablation_v2,
    write_benchmark_core_report,
    aggregate_run_artifacts,
)
import json


def aggregate_all_task_runs(workspace_root: Path, output_path: Path):
    """
    聚合所有任务目录下的 run 工件。

    遍历 workspace_root 下的所有任务目录，收集每个任务的 .pico/runs/ 下的 run 目录，
    然后调用 aggregate_run_artifacts 进行聚合，最后保存到 output_path。
    """
    workspace_root = Path(workspace_root)
    output_path = Path(output_path)

    # 收集所有任务的 runs 目录
    all_runs_data = {}
    total_runs = 0

    for task_dir in sorted(workspace_root.iterdir()):
        if not task_dir.is_dir():
            continue

        # 找到任务下的 .pico/runs 目录
        # 结构：task_dir/fixture_repo/.pico/runs/
        for fixture_dir in task_dir.iterdir():
            if not fixture_dir.is_dir():
                continue
            runs_dir = fixture_dir / ".pico" / "runs"
            if not runs_dir.exists():
                continue

            # 对这个任务的 runs 目录进行聚合
            task_runs = aggregate_run_artifacts(runs_dir)
            all_runs_data[task_dir.name] = task_runs
            total_runs += task_runs["run_count"]

    # 生成总体聚合报告
    result = {
        "workspace_root": str(workspace_root),
        "task_count": len(all_runs_data),
        "total_run_count": total_runs,
        "per_task_runs": all_runs_data,
        # 计算所有任务的平均值
        "aggregated_summary": {
            "avg_tool_steps": sum(r["avg_tool_steps"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_attempts": sum(r["avg_attempts"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_prompt_chars": sum(r["avg_prompt_chars"] for r in all_runs_data.values()) / len(all_runs_data),
            "cache_hit_rate": sum(r["cache_hit_rate"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_cached_tokens": sum(r["avg_cached_tokens"] for r in all_runs_data.values()) / len(all_runs_data),
            "prefix_reuse_rate": sum(r["prefix_reuse_rate"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_run_duration_ms": sum(r["avg_run_duration_ms"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_tool_duration_ms": sum(r["avg_tool_duration_ms"] for r in all_runs_data.values()) / len(all_runs_data),
            "avg_prompt_build_duration_ms": sum(r["avg_prompt_build_duration_ms"] for r in all_runs_data.values()) / len(all_runs_data),
        }
    }

    # 保存到文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] 运行工件聚合完成: {output_path}")
    print(f"     任务数: {result['task_count']}, 总运行数: {result['total_run_count']}")
    return result


if __name__ == "__main__":
    out = Path("benchmarks/results/main-resume-repro-2026-06-30")
    # run_harness_regression_v2(
    #     benchmark_path=Path("benchmarks/coding_tasks.json"),
    #     artifact_path=out / "harness-regression-v2.json",
    #     workspace_root=Path("tmp/pico-main-resume-workspaces"),
    # )  # 当前项目目录下的tmp文件夹中有workspace中的相关文件
    # run_context_ablation_v2(out / "context-ablation-v2.json", repetitions=5)
    # run_memory_ablation_v2(out / "memory-ablation-v2.json", repetitions=5)
    # run_recovery_ablation_v2(out / "recovery-ablation-v2.json", repetitions=3)
    # write_benchmark_core_report(
    #     report_path=out / "pico-benchmark-core-report.md",
    #     harness_artifact_path=out / "harness-regression-v2.json",
    #     context_artifact_path=out / "context-ablation-v2.json",
    #     memory_artifact_path=out / "memory-ablation-v2.json",
    #     recovery_artifact_path=out / "recovery-ablation-v2.json",
    # )

    # 聚合所有任务的 run 工件
    aggregate_all_task_runs(
        workspace_root=Path("tmp/pico-main-resume-workspaces"),
        output_path=out / "runs-aggregation.json",
    )