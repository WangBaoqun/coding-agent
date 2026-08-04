"""测试 ContextManager 中的 skills 集成"""
from pico.skills.models import Skill, Parameter, CodeBlock
from pico.skills.inventory import SkillsInventory
from pico.context_manager import ContextManager


def create_mock_agent(skills=None):
    """创建模拟 agent 对象用于测试"""
    class MockAgent:
        def __init__(self, skills_list=None):
            # 创建技能清单
            if skills_list is None:
                skills_list = []
            self.skills_inventory = SkillsInventory(skills_list)
            # 模拟其他必要属性
            self.prefix = "System rules and tools info"
            self.session = {"history": []}
            self.memory = None

        def memory_text(self):
            return "Memory:\n- task_summary: test task"

        def feature_enabled(self, feature_name):
            return True

    return MockAgent(skills)


def create_test_skill(name: str, description: str, category: str = "") -> Skill:
    """创建测试用的 Skill 对象"""
    return Skill(
        name=name,
        description=description,
        category=category,
        parameters=[],
        content="",
        content_type="prompt_only",
        code_blocks=[],
        file_path=f".pico/skills/{name}.md"
    )


def test_skills_section_in_section_order():
    """测试 skills 在 SECTION_ORDER 中"""
    from pico.context_manager import SECTION_ORDER
    assert "skills" in SECTION_ORDER
    # skills 应该在 prefix 之后，memory 之前
    prefix_idx = SECTION_ORDER.index("prefix")
    skills_idx = SECTION_ORDER.index("skills")
    memory_idx = SECTION_ORDER.index("memory")
    assert prefix_idx < skills_idx < memory_idx
    print("✅ skills 在 SECTION_ORDER 中位置正确")


def test_skills_in_reduction_order():
    """测试 skills 在 DEFAULT_REDUCTION_ORDER 中"""
    from pico.context_manager import DEFAULT_REDUCTION_ORDER
    assert "skills" in DEFAULT_REDUCTION_ORDER
    # skills 应该在 relevant_memory 之后，history 之前
    relevant_idx = DEFAULT_REDUCTION_ORDER.index("relevant_memory")
    skills_idx = DEFAULT_REDUCTION_ORDER.index("skills")
    history_idx = DEFAULT_REDUCTION_ORDER.index("history")
    assert relevant_idx < skills_idx < history_idx
    print("✅ skills 在 DEFAULT_REDUCTION_ORDER 中位置正确")


def test_skills_budget_config():
    """测试 skills 预算配置"""
    from pico.context_manager import DEFAULT_SECTION_BUDGETS, DEFAULT_SECTION_FLOORS
    assert "skills" in DEFAULT_SECTION_BUDGETS
    assert "skills" in DEFAULT_SECTION_FLOORS
    # skills 预算应该是 600（约 5% 总预算）
    assert DEFAULT_SECTION_BUDGETS["skills"] == 600
    # skills 最小预算应该是 200
    assert DEFAULT_SECTION_FLOORS["skills"] == 200
    print("✅ skills 预算配置正确")


def test_context_manager_with_no_skills():
    """测试没有技能的 ContextManager"""
    agent = create_mock_agent(skills=[])
    cm = ContextManager(agent)

    prompt, metadata = cm.build("test request")

    # 应该包含 skills section，但内容为空
    assert "skills" in metadata["sections"]
    assert metadata["skills"]["raw_chars"] == 0
    assert metadata["skills"]["skills_count"] == 0
    print("✅ 无技能时 ContextManager 正常工作")


def test_context_manager_with_skills():
    """测试有技能的 ContextManager"""
    skills = [
        create_test_skill("code-review", "Review code for bugs"),
        create_test_skill("hello", "A greeting skill"),
    ]
    agent = create_mock_agent(skills=skills)
    cm = ContextManager(agent)

    prompt, metadata = cm.build("test request")

    # 应该包含 skills section
    assert "skills" in metadata["sections"]
    assert metadata["skills"]["skills_count"] == 2
    assert metadata["skills"]["raw_chars"] > 0
    # prompt 中应该包含技能清单
    assert "Available Skills" in prompt
    assert "code-review" in prompt
    assert "hello" in prompt
    print("✅ 有技能时 ContextManager 正常工作")


def test_skills_section_rendering():
    """测试 skills section 的渲染"""
    skills = [create_test_skill("test-skill", "Test description")]
    agent = create_mock_agent(skills=skills)
    cm = ContextManager(agent)

    # 测试 _render_skills_section 方法
    rendered = cm._render_skills_section()
    assert "Available Skills" in rendered
    assert "test-skill" in rendered
    assert "Test description" in rendered
    print("✅ skills section 渲染正确")


def test_skills_budget_enforcement():
    """测试 skills 预算限制"""
    # 创建大量技能，使清单超过预算
    skills = [create_test_skill(f"skill{i}", f"Description for skill {i}") for i in range(100)]
    agent = create_mock_agent(skills=skills)
    cm = ContextManager(agent, total_budget=12000)

    prompt, metadata = cm.build("test request")

    # skills section 应该被裁剪到预算内
    skills_renderended = metadata["skills"]["rendered_chars"]
    skills_budget = metadata["sections"]["skills"]["budget_chars"]
    assert skills_renderended <= skills_budget
    print(f"✅ skills 预算限制生效（渲染: {skills_renderended} chars, 预算: {skills_budget} chars）")


def test_assemble_prompt_order():
    """测试 prompt 组装顺序"""
    skills = [create_test_skill("test", "test")]
    agent = create_mock_agent(skills=skills)
    cm = ContextManager(agent)

    prompt, metadata = cm.build("my request")

    # 验证顺序：prefix → skills → memory → relevant_memory → history → current_request
    prefix_pos = prompt.find("System rules")
    skills_pos = prompt.find("Available Skills")
    memory_pos = prompt.find("Memory:")
    request_pos = prompt.find("Current user request:")

    assert prefix_pos < skills_pos, "prefix 应该在 skills 之前"
    assert skills_pos < memory_pos, "skills 应该在 memory 之前"
    assert memory_pos < request_pos, "memory 应该在 current_request 之前"
    assert "my request" in prompt
    print("✅ prompt 组装顺序正确")


if __name__ == "__main__":
    test_skills_section_in_section_order()
    test_skills_in_reduction_order()
    test_skills_budget_config()
    test_context_manager_with_no_skills()
    test_context_manager_with_skills()
    test_skills_section_rendering()
    test_skills_budget_enforcement()
    test_assemble_prompt_order()
    print("\n✅ 所有 ContextManager Skills 集成测试通过!")
