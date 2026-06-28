"""调试记忆依赖实验的脚本。

使用方法：
    python tests/debug_memory_experiment.py
"""
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pico.metrics import (
    run_memory_dependency_experiment,
    run_large_scale_memory_experiment,
    _run_memory_variant,
    _run_memory_task_variant,
    MEMORY_EXPERIMENT_TASKS,
)


def debug_single_task():
    """调试单个任务的执行过程"""
    print("=" * 60)
    print("调试 1: 单个任务执行过程")
    print("=" * 60)

    task = MEMORY_EXPERIMENT_TASKS[11]  # fact_color: "deploy key is red"
    print(f"  任务 ID: {task['id']}")
    print(f"  类别: {task['category']}")
    print(f"  文件: {task['filename']}")
    print(f"  事实: {task['fact']}")
    print()
    # memory_on的结果：True，工具步数：0，重试次数：1，重复读取：0
    # memory_off和memory_irrelevant的结果：True, 工具步数：1，重试次数：2，重复读取：1
    for variant in ["memory_on", "memory_off", "memory_irrelevant"]:
        print(f"  --- 变体: {variant} ---")
        result = _run_memory_task_variant(task, variant)
        print(f"    正确: {result['correct']}")
        print(f"    工具步数: {result['tool_steps']}")
        print(f"    重试次数: {result['attempts']}")
        print(f"    重复读取: {result['repeated_reads']}")
        print()


def debug_memory_dependency_experiment():
    """调试记忆依赖实验"""
    print("=" * 60)
    print("调试 2: 记忆依赖实验 (repetitions=1)")
    print("=" * 60)

    results = run_memory_dependency_experiment(repetitions=1)

    for variant, data in results.items():
        print(f"  {variant}:")
        print(f"    重复读取: {data['repeated_reads']}")
        print(f"    平均工具步数: {data['avg_tool_steps']:.2f}")
        print(f"    平均重试次数: {data['avg_attempts']:.2f}")
        print(f"    正确率: {data['correct_rate']:.1%}")
        print()


def debug_large_scale_memory_experiment():
    """调试大规模记忆实验"""
    print("=" * 60)
    print("调试 3: 大规模记忆实验 (repetitions=1)")
    print("=" * 60)

    results = run_large_scale_memory_experiment(repetitions=1)

    print(f"  任务数: {results['task_count']}")
    print()

    for variant, data in results['variants'].items():
        print(f"  {variant}:")
        print(f"    重复读取: {data['repeated_reads']}")
        print(f"    平均工具步数: {data['avg_tool_steps']:.2f}")
        print(f"    正确率: {data['correct_rate']:.1%}")
        print()



def debug_model_client_logic():
    """调试 _MemoryExperimentModelClient 的判断逻辑"""
    print("=" * 60)
    print("调试 4: 模型客户端判断逻辑")
    print("=" * 60)

    from pico.metrics import _MemoryExperimentModelClient

    client = _MemoryExperimentModelClient("deploy key is red", "facts.txt")

    # 模拟 bootstrap 阶段
    print("  Bootstrap 阶段:")
    print(f"    phase: {client.phase}")
    output1 = client.complete("dummy prompt", 100)
    print(f"    输出: {output1}")
    print(f"    phase: {client.phase}")

    output2 = client.complete("dummy prompt", 100)
    print(f"    输出: {output2}")
    print(f"    phase: {client.phase}")
    print()

    # 模拟 followup 阶段
    print("  Followup 阶段:")

    # 场景 1: prompt 中包含记忆
    prompt_with_memory = """
Memory:
- deploy key is red

Relevant memory:
- deploy key is red

Transcript:
- empty

Current user request:
What color is the deploy key?
"""
    print("    场景 1: prompt 中包含记忆")
    output3 = client.complete(prompt_with_memory, 100)
    print(f"      输出: {output3}")
    print(f"      followup_reads: {client.followup_reads}")
    print()

    # 重置 phase
    client.phase = "question"

    # 场景 2: prompt 中不包含记忆
    prompt_without_memory = """
Memory:
- disabled

Relevant memory:
- none

Transcript:
- empty

Current user request:
What color is the deploy key?
"""
    print("    场景 2: prompt 中不包含记忆")
    output4 = client.complete(prompt_without_memory, 100)
    print(f"      输出: {output4}")
    print(f"      followup_reads: {client.followup_reads}")


if __name__ == "__main__":
    debug_single_task()
    # debug_memory_dependency_experiment()  # 这个和debug_single_task()基本相同
    debug_large_scale_memory_experiment()
    debug_model_client_logic()

    print()
    print("=" * 60)
    print("调试完成！")
    print("=" * 60)
