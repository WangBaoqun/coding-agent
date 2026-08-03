"""测试异常类"""
from pico.skills.exceptions import (
    SkillNotFoundError,
    SkillValidationError,
    SkillExecutionError,
    SkillPermissionDeniedError
)


def test_skill_not_found():
    """测试技能不存在异常"""
    try:
        raise SkillNotFoundError(
            skill_name="code-reviews",
            available_skills=["code-review", "hello", "generate-tests"]
        )
    except SkillNotFoundError as e:
        print(f"✅ 错误消息: {e}")
        print(f"✅ 技能名称: {e.skill_name}")
        print(f"✅ 建议: {e.suggestions}")
        assert e.skill_name == "code-reviews"
        assert "code-review" in e.suggestions


def test_skill_validation_error():
    """测试验证失败异常"""
    try:
        raise SkillValidationError(
            file_path=".pico/skills/invalid.md",
            validation_errors=["缺少必填字段: name", "description 超过100字符"]
        )
    except SkillValidationError as e:
        print(f"✅ 错误消息: {e}")
        print(f"✅ 文件路径: {e.file_path}")
        print(f"✅ 错误数量: {len(e.validation_errors)}")
        assert e.file_path == ".pico/skills/invalid.md"
        assert len(e.validation_errors) == 2


def test_skill_execution_error():
    """测试执行失败异常"""
    original_error = ZeroDivisionError("division by zero")
    try:
        raise SkillExecutionError(
            skill_name="run-python",
            original_error=original_error,
            execution_context={"code": "print(1/0)"}
        )
    except SkillExecutionError as e:
        print(f"✅ 错误消息: {e}")
        print(f"✅ 技能名称: {e.skill_name}")
        print(f"✅ 原始错误: {e.original_error}")
        assert e.skill_name == "run-python"
        assert isinstance(e.original_error, ZeroDivisionError)


def test_skill_permission_denied():
    """测试权限拒绝异常"""
    try:
        raise SkillPermissionDeniedError(
            skill_name="dangerous-skill",
            reason="用户选择拒绝执行"
        )
    except SkillPermissionDeniedError as e:
        print(f"✅ 错误消息: {e}")
        print(f"✅ 技能名称: {e.skill_name}")
        print(f"✅ 原因: {e.reason}")
        assert e.skill_name == "dangerous-skill"


if __name__ == "__main__":
    print("测试异常类...\n")
    test_skill_not_found()
    print()
    test_skill_validation_error()
    print()
    test_skill_execution_error()
    print()
    test_skill_permission_denied()
    print("\n✅ 所有测试通过!")
