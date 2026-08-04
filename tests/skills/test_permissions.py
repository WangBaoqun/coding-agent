"""测试技能权限管理器"""
import tempfile
from pathlib import Path
from pico.skills.permissions import SkillPermissions


def test_load_empty_permissions():
    """测试加载空的权限文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 文件不存在时应该返回空字典
        assert perms.permissions == {}
        assert perms.has_permission("hello") is None
        print("✅ 空权限文件测试通过")


def test_grant_permission():
    """测试授权技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 授权技能（会话权限）
        perms.grant_permission("hello", always=False)

        # 验证权限已保存（在内存中）
        assert perms.has_permission("hello") is True
        assert perms.get_permission_status("hello") == "allowed"

        # 验证文件未写入（会话权限不保存到文件）
        assert not perm_file.exists()
        print("✅ 授权技能测试通过")


def test_grant_always_permission():
    """测试设置 always allow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 设置 always allow
        perms.grant_permission("hello", always=True)

        # 验证权限已保存
        assert perms.has_permission("hello") is True
        assert perms.get_permission_status("hello") == "always"
        print("✅ Always allow 测试通过")


def test_deny_permission():
    """测试拒绝技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 拒绝技能
        perms.deny_permission("hello")

        # 验证权限已保存
        assert perms.has_permission("hello") is False
        assert perms.get_permission_status("hello") == "denied"
        print("✅ 拒绝技能测试通过")


def test_check_permission_with_prompt():
    """测试带提示的权限检查"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 定义提示函数（模拟用户选择 "allow"）
        def prompt_allow(skill_name):
            return "allow"

        # 首次检查，应该提示用户
        result = perms.check_permission("hello", prompt_fn=prompt_allow)
        assert result is True
        assert perms.has_permission("hello") is True

        # 再次检查，不应该提示（已授权）
        result = perms.check_permission("hello", prompt_fn=lambda x: "deny")
        assert result is True  # 仍然返回 True，因为已授权
        print("✅ 带提示的权限检查测试通过")


def test_check_permission_deny():
    """测试拒绝权限"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 定义提示函数（模拟用户选择 "deny"）
        def prompt_deny(skill_name):
            return "deny"

        result = perms.check_permission("hello", prompt_fn=prompt_deny)
        assert result is False
        assert perms.has_permission("hello") is False
        print("✅ 拒绝权限测试通过")


def test_check_permission_without_prompt():
    """测试没有提示函数时的权限检查"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 没有提示函数，首次使用应该返回 False
        result = perms.check_permission("hello", prompt_fn=None)
        assert result is False
        print("✅ 无提示函数测试通过")


def test_persistence_across_instances():
    """测试权限在多个实例间持久化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"

        # 第一个实例：授权
        perms1 = SkillPermissions(str(perm_file))
        perms1.grant_permission("hello", always=True)

        # 第二个实例：应该能读取权限
        perms2 = SkillPermissions(str(perm_file))
        assert perms2.has_permission("hello") is True
        assert perms2.get_permission_status("hello") == "always"
        print("✅ 权限持久化测试通过")


def test_list_permissions():
    """测试列出所有权限"""
    with tempfile.TemporaryDirectory() as tmpdir:
        perm_file = Path(tmpdir) / "permissions.json"
        perms = SkillPermissions(str(perm_file))

        # 添加多个权限
        perms.grant_permission("skill1", always=False)
        perms.grant_permission("skill2", always=True)
        perms.deny_permission("skill3")

        # 列出所有权限
        all_perms = perms.list_permissions()
        assert len(all_perms) == 3
        assert all_perms["skill1"] == "allowed"
        assert all_perms["skill2"] == "always"
        assert all_perms["skill3"] == "denied"
        print("✅ 列出所有权限测试通过")


if __name__ == "__main__":
    test_load_empty_permissions()
    test_grant_permission()
    test_grant_always_permission()
    test_deny_permission()
    test_check_permission_with_prompt()
    test_check_permission_deny()
    test_check_permission_without_prompt()
    test_persistence_across_instances()
    test_list_permissions()
    print("\n✅ 所有权限管理器测试通过!")
