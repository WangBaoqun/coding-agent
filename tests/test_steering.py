"""手动测试 steering 机制

使用方法:
    pytest tests/test_steering_manual.py -v -s

测试内容:
    1. 基础 steering 功能（队列、消费、history 注入）
    2. 队列边界行为（FIFO、上限、空白过滤）
    3. 双检查点机制（循环开头 + 循环结尾）
"""

import threading
import time
from pathlib import Path

from pico import FakeModelClient, MiniAgent, SessionStore, WorkspaceContext


def build_workspace(tmp_path):
    """构建测试工作区"""
    (tmp_path / "README.md").write_text("# Test Project\n\nThis is a test.\n", encoding="utf-8")
    (tmp_path / "file1.txt").write_text("content1\n", encoding="utf-8")
    (tmp_path / "file2.txt").write_text("content2\n", encoding="utf-8")
    return WorkspaceContext.build(tmp_path)


def build_agent(tmp_path, outputs, **kwargs):
    """构建测试 Agent"""
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


def test_basic_steering_injection(tmp_path):
    """测试基础 steering 功能：steering 被注入到 history"""
    # 1. 创建 Agent，配置多步任务的脚本输出
    agent = build_agent(
        tmp_path,
        [
            # Step 1: 读取 file1.txt
            '<tool>{"name":"read_file","args":{"path":"file1.txt"}}</tool>',
            # Step 2: 读取 file2.txt
            '<tool>{"name":"read_file","args":{"path":"file2.txt"}}</tool>',
            # Step 3: 最终回答
            "<final>Task completed.</final>",
        ],
    )
    agent._steering_enabled = True

    # 2. 直接注入 steering 到队列（不依赖输入线程）
    # 在后台线程中延迟注入，模拟用户在 Agent 执行期间输入
    def inject_steering():
        time.sleep(0.1)  # 等待 Agent 开始执行
        agent.steering_queue.put_nowait({
            "text": "停下来，先看看 README",
            "arrived_at": time.time()
        })

    steering_thread = threading.Thread(target=inject_steering, daemon=True)
    steering_thread.start()

    # 3. 执行任务
    result = agent.ask("Analyze files")
    steering_thread.join(timeout=1)  # 等待注入线程完成

    # 4. 验证 steering 被注入到 history
    steering_msgs = [
        msg for msg in agent.session["history"]
        if "[steering]" in msg.get("content", "")
    ]

    assert len(steering_msgs) > 0, "Steering 应该被注入到 history"
    assert steering_msgs[0]["role"] == "user"
    assert "[steering] 停下来，先看看 README" in steering_msgs[0]["content"]

    # 5. 验证 trace 事件（steering_consumed 应该有）
    trace_file = Path(agent.current_run_dir) / "trace.jsonl"
    assert trace_file.exists(), "Trace 文件应该存在"

    import json
    all_events = []
    steering_events = []
    for line in trace_file.read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        all_events.append(event)
        # 注意：trace 事件使用 "event" 字段，不是 "event_type"
        if event.get("event", "").startswith("steering_"):
            steering_events.append(event)

    # 调试：打印所有事件类型
    print(f"\n所有事件类型: {[e.get('event') for e in all_events]}")
    print(f"Steering 事件: {steering_events}")

    # steering_consumed 事件应该在 _consume_steering() 中 emit
    consumed_events = [e for e in steering_events if e.get("event") == "steering_consumed"]
    assert len(consumed_events) > 0, f"应该有 steering_consumed 事件。所有事件: {[e.get('event') for e in all_events]}"


def test_steering_not_injected_when_disabled(tmp_path):
    """测试 steering 未启用时不被消费"""
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":{"path":"file1.txt"}}</tool>',
            "<final>Done.</final>",
        ],
    )
    agent._steering_enabled = False  # 禁用 steering

    # 注入 steering（但应该不被消费）
    agent.steering_queue.put_nowait({
        "text": "This should be ignored",
        "arrived_at": time.time()
    })

    result = agent.ask("Test task")

    # 验证 steering 未被消费
    steering_msgs = [
        msg for msg in agent.session["history"]
        if "[steering]" in msg.get("content", "")
    ]

    assert len(steering_msgs) == 0, "Steering 未启用时不应该被注入"


def test_queue_fifo_order(tmp_path):
    """测试队列 FIFO 顺序"""
    agent = build_agent(tmp_path, ["<final>Done.</final>"])
    agent._steering_enabled = True

    # 入队 3 条消息
    agent.steering_queue.put_nowait({"text": "第一条", "arrived_at": time.time()})
    agent.steering_queue.put_nowait({"text": "第二条", "arrived_at": time.time()})
    agent.steering_queue.put_nowait({"text": "第三条", "arrived_at": time.time()})

    # 验证出队顺序
    first = agent.steering_queue.get_nowait()
    second = agent.steering_queue.get_nowait()
    third = agent.steering_queue.get_nowait()

    assert first["text"] == "第一条"
    assert second["text"] == "第二条"
    assert third["text"] == "第三条"


def test_queue_limit(tmp_path):
    """测试队列上限（10 条）"""
    agent = build_agent(tmp_path, ["<final>Done.</final>"])
    agent._steering_enabled = True

    # 尝试入队 15 条消息
    for i in range(15):
        try:
            agent.steering_queue.put_nowait({
                "text": f"消息{i}",
                "arrived_at": time.time()
            })
        except Exception:
            # 队列满时 put_nowait 会抛异常
            # 但我们的实现应该在 _read_loop 中处理这种情况
            pass

    # 队列大小应该 <= 10
    assert agent.steering_queue.qsize() <= 10, f"队列大小应该 <= 10，实际为 {agent.steering_queue.qsize()}"


def test_empty_queue_no_error(tmp_path):
    """测试空队列时 _consume_steering() 不报错"""
    agent = build_agent(tmp_path, ["<final>Done.</final>"])
    agent._steering_enabled = True

    # 队列为空时调用 _consume_steering() 不应该报错
    agent._consume_steering()

    # 验证没有异常
    assert True


def test_steering_does_not_consume_tool_step(tmp_path):
    """测试 steering 不消耗 tool_step"""
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":{"path":"file1.txt"}}</tool>',
            "<final>Done.</final>",
        ],
    )
    agent._steering_enabled = True

    # 注入 steering
    agent.steering_queue.put_nowait({
        "text": "Test steering",
        "arrived_at": time.time()
    })

    initial_tool_steps = 0

    def inject_and_check():
        nonlocal initial_tool_steps
        time.sleep(0.1)
        initial_tool_steps = agent.current_task_state.tool_steps if agent.current_task_state else 0

    thread = threading.Thread(target=inject_and_check, daemon=True)
    thread.start()

    result = agent.ask("Test task")

    # 验证 tool_steps 只增加了 1（只有 read_file 这一次工具调用）
    # steering 不应该消耗 tool_step
    final_tool_steps = agent.current_task_state.tool_steps
    assert final_tool_steps == 1, f"tool_steps 应该为 1，实际为 {final_tool_steps}"


def test_steering_cleared_after_ask(tmp_path):
    """测试 ask() 返回后队列被清空"""
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"read_file","args":{"path":"file1.txt"}}</tool>',
            "<final>Done.</final>",
        ],
    )
    agent._steering_enabled = True

    # 注入 3 条 steering（只消费 1 条）
    for i in range(3):
        agent.steering_queue.put_nowait({
            "text": f"Steering {i}",
            "arrived_at": time.time()
        })

    result = agent.ask("Test task")

    # 验证 ask() 返回后队列被清空
    assert agent.steering_queue.qsize() == 0, "ask() 返回后队列应该被清空"
    assert agent._steering_input_thread is None, "输入线程应该被清理"


def test_blank_content_filtered(tmp_path):
    """测试空白内容不入队"""
    agent = build_agent(tmp_path, ["<final>Done.</final>"])
    agent._steering_enabled = True

    # 模拟 _read_loop 的过滤逻辑
    test_inputs = ["", "   ", "\n", "有效内容"]
    for text in test_inputs:
        if text.strip():  # 这是 _read_loop 中的过滤逻辑
            agent.steering_queue.put_nowait({
                "text": text.strip(),
                "arrived_at": time.time()
            })

    # 只有 "有效内容" 应该入队
    assert agent.steering_queue.qsize() == 1, f"应该只有 1 条消息入队，实际为 {agent.steering_queue.qsize()}"

    msg = agent.steering_queue.get_nowait()
    assert msg["text"] == "有效内容"


def test_consume_steering_performance(tmp_path):
    """测试 _consume_steering() 性能开销 < 5ms（T026）"""
    agent = build_agent(tmp_path, ["<final>Done.</final>"])
    agent._steering_enabled = True

    # 预热
    for _ in range(10):
        agent._consume_steering()

    # 测量 100 次空队列检查的平均耗时
    times = []
    for _ in range(100):
        start = time.monotonic()
        agent._consume_steering()
        elapsed_ms = (time.monotonic() - start) * 1000
        times.append(elapsed_ms)

    avg_ms = sum(times) / len(times)
    max_ms = max(times)

    # SC-003: 额外开销 < 5ms
    assert avg_ms < 5, f"平均耗时 {avg_ms:.3f}ms 超过 5ms 限制"
    assert max_ms < 10, f"最大耗时 {max_ms:.3f}ms 超过 10ms（可能有 GC 抖动）"
