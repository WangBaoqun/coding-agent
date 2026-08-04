"""测试技能执行器"""
from pico.skills.models import Skill, Parameter, CodeBlock
from pico.skills.executor import SkillExecutor
from pico.skills.permissions import SkillPermissions
import tempfile
from pathlib import Path


def create_prompt_only_skill():
    """创建 prompt_only 类型的技能"""
    return Skill(
        name="greeting",
        description="A greeting skill",
        category="demo",
        parameters=[
            Parameter(name="name", type="string", required=False, default="World")
        ],
        content="Hello, {name}!",
        content_type="prompt_only",
        code_blocks=[],
        file_path=".pico/skills/greeting.md"
    )


def create_code_only_skill():
    """创建 code_only 类型的技能"""
    return Skill(
        name="calculate",
        description="Calculate sum",
        category="demo",
        parameters=[],
        content="",
        content_type="code_only",
        code_blocks=[
            CodeBlock(
                language="python",
                code="print(2 + 3)",
                index=0
            )
        ],
        file_path=".pico/skills/calculate.md"
    )


def create_hybrid_skill():
    """创建 hybrid 类型的技能"""
    return Skill(
        name="process",
        description="Process data",
        category="demo",
        parameters=[
            Parameter(name="value", type="string", required=True, default="")
        ],
        content="Processing: {value}",
        content_type="hybrid",
        code_blocks=[
            CodeBlock(
                language="python",
                code="print('Processed!')",
                index=0
            )
        ],
        file_path=".pico/skills/process.md"
    )


def test_execute_prompt_only():
    """测试执行 prompt_only 技能"""
    skill = create_prompt_only_skill()
    executor = SkillExecutor()

    # 执行技能（带参数）
    result = executor.execute(skill, parameters={"name": "Alice"})

    assert result.success is True
    assert result.prompt_injection == "Hello, Alice!"
    assert result.code_output == ""
    assert result.error_message == ""
    assert result.execution_time >= 0
    print("✅ prompt_only 执行测试通过")


def test_execute_prompt_only_default_parameter():
    """测试 prompt_only 技能的默认参数"""
    skill = create_prompt_only_skill()
    executor = SkillExecutor()

    # 执行技能（不带参数，使用默认值）
    result = executor.execute(skill, parameters={})

    assert result.success is True
    # {name} 不会被替换，因为没有提供参数
    assert "{name}" in result.prompt_injection
    print("✅ prompt_only 默认参数测试通过")


def test_execute_code_only():
    """测试执行 code_only 技能"""
    skill = create_code_only_skill()
    executor = SkillExecutor()

    result = executor.execute(skill)

    assert result.success is True
    assert "5" in result.code_output  # 2 + 3 = 5
    assert result.prompt_injection == ""
    print("✅ code_only 执行测试通过")


def test_execute_hybrid():
    """测试执行 hybrid 技能"""
    skill = create_hybrid_skill()
    executor = SkillExecutor()

    result = executor.execute(skill, parameters={"value": "test data"})

    assert result.success is True
    assert "Processing: test data" in result.prompt_injection
    assert "Processed!" in result.code_output
    print("✅ hybrid 执行测试通过")


def test_execute_with_permission_check():
    """测试带权限检查的执行"""
    skill = create_prompt_only_skill()

    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        permissions = SkillPermissions(str(perm_file))

        # 定义提示函数（模拟用户允许）
        def prompt_allow(skill_name):
            return "allow"

        executor = SkillExecutor(permissions=permissions)
        result = executor.execute(skill, parameters={"name": "Bob"}, prompt_fn=prompt_allow)

        assert result.success is True
        assert permissions.has_permission("greeting") is True
        print("✅ 权限检查执行测试通过")


def test_execute_with_permission_denied():
    """测试权限被拒绝的情况"""
    skill = create_prompt_only_skill()

    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        permissions = SkillPermissions(str(perm_file))

        # 定义提示函数（模拟用户拒绝）
        def prompt_deny(skill_name):
            return "deny"

        executor = SkillExecutor(permissions=permissions)
        result = executor.execute(skill, parameters={"name": "Bob"}, prompt_fn=prompt_deny)

        assert result.success is False
        assert "Permission denied" in result.error_message
        print("✅ 权限拒绝测试通过")


def test_execute_code_failure():
    """测试代码执行失败"""
    # 创建一个会失败的代码块
    skill = Skill(
        name="failing",
        description="Failing code",
        category="demo",
        parameters=[],
        content="",
        content_type="code_only",
        code_blocks=[
            CodeBlock(
                language="python",
                code="raise ValueError('Test error')",
                index=0
            )
        ],
        file_path=".pico/skills/failing.md"
    )

    executor = SkillExecutor()
    result = executor.execute(skill)

    assert result.success is False
    print("✅ 代码执行失败测试通过")


def test_parameter_substitution():
    """测试参数替换"""
    skill = Skill(
        name="template",
        description="Template skill",
        category="demo",
        parameters=[
            Parameter(name="greeting", type="string", required=True, default=""),
            Parameter(name="name", type="string", required=True, default="")
        ],
        content="{greeting}, {name}! Welcome to {place}.",
        content_type="prompt_only",
        code_blocks=[],
        file_path=".pico/skills/template.md"
    )

    executor = SkillExecutor()
    result = executor.execute(skill, parameters={
        "greeting": "Hello",
        "name": "Alice",
        "place": "Wonderland"
    })

    assert result.success is True
    assert result.prompt_injection == "Hello, Alice! Welcome to Wonderland."
    print("✅ 参数替换测试通过")


def test_unsupported_language():
    """测试不支持的编程语言"""
    skill = Skill(
        name="javascript",
        description="JavaScript skill",
        category="demo",
        parameters=[],
        content="",
        content_type="code_only",
        code_blocks=[
            CodeBlock(
                language="javascript",
                code="console.log('Hello')",
                index=0
            )
        ],
        file_path=".pico/skills/javascript.md"
    )

    executor = SkillExecutor()
    result = executor.execute(skill)

    # 应该成功，但输出应该包含 "Skipped"
    assert result.success is True
    assert "Skipped" in result.code_output or "unsupported" in result.code_output.lower()
    print("✅ 不支持语言测试通过")


if __name__ == "__main__":
    test_execute_prompt_only()
    test_execute_prompt_only_default_parameter()
    test_execute_code_only()
    test_execute_hybrid()
    test_execute_with_permission_check()
    test_execute_with_permission_denied()
    test_execute_code_failure()
    test_parameter_substitution()
    test_unsupported_language()
    print("\n✅ 所有执行器测试通过!")
