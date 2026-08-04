"""
技能权限管理器 - 处理技能执行的权限确认

这个模块负责:
1. 加载/保存权限配置
2. 检查技能是否已被确认
3. 首次使用时提示用户确认
4. 支持 "always allow" 选项

使用示例:
    from pico.skills.permissions import SkillPermissions

    permissions = SkillPermissions(".pico/skill_permissions.json")

    # 检查是否可以执行（会提示用户如果需要）
    if permissions.check_permission("hello"):
        # 执行技能
        pass
"""
import json
from pathlib import Path
from typing import Optional


class SkillPermissions:
    """
    技能权限管理器

    属性:
        permissions_file: 权限配置文件路径
        permissions: 权限字典 {skill_name: "allowed" | "denied" | "always"}

    方法:
        check_permission(skill_name): 检查是否可以执行技能
        grant_permission(skill_name, always=False): 授权技能
        deny_permission(skill_name): 拒绝技能
        has_permission(skill_name): 检查是否已授权（不提示）
    """

    def __init__(self, permissions_file: str = ".pico/skill_permissions.json"):
        """
        初始化权限管理器

        参数:
            permissions_file: 权限配置文件路径
        """
        self.permissions_file = Path(permissions_file)
        self.permissions = self._load_permissions()  # 永久权限（从文件加载）
        self.session_permissions = {}  # 会话权限（只在内存中，不保存到文件）

    def _load_permissions(self) -> dict:
        """
        从文件加载权限配置

        返回:
            dict: 权限字典
        """
        if not self.permissions_file.exists():
            return {}

        try:
            with open(self.permissions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # 如果文件损坏，返回空字典
            return {}

    def _save_permissions(self):
        """保存权限配置到文件"""
        # 确保目录存在
        self.permissions_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.permissions_file, "w", encoding="utf-8") as f:
            json.dump(self.permissions, f, indent=2, ensure_ascii=False)

    def has_permission(self, skill_name: str) -> Optional[bool]:
        """
        检查技能是否已授权（不提示用户）

        参数:
            skill_name: 技能名称

        返回:
            Optional[bool]: True=已授权, False=已拒绝, None=未确认
        """
        # 先检查会话权限（优先级更高）
        if skill_name in self.session_permissions:
            status = self.session_permissions[skill_name]
            if status == "allowed" or status == "always":
                return True
            elif status == "denied":
                return False

        # 再检查永久权限
        if skill_name not in self.permissions:
            return None

        status = self.permissions[skill_name]
        if status == "always":  # 只有 "always" 才算已授权（"allowed" 在会话权限中）
            return True
        elif status == "denied":
            return False
        return None

    def grant_permission(self, skill_name: str, always: bool = False):
        """
        授权技能

        参数:
            skill_name: 技能名称
            always: 是否设置为 "always allow"（永久保存）
        """
        if always:
            # 永久授权：保存到文件
            self.permissions[skill_name] = "always"
            self._save_permissions()
        else:
            # 会话授权：只保存到内存
            self.session_permissions[skill_name] = "allowed"

    def deny_permission(self, skill_name: str):
        """
        拒绝技能

        参数:
            skill_name: 技能名称
        """
        self.permissions[skill_name] = "denied"
        self._save_permissions()

    def check_permission(self, skill_name: str, prompt_fn=None) -> bool:
        """
        检查是否可以执行技能（会提示用户如果需要）

        参数:
            skill_name: 技能名称
            prompt_fn: 提示函数，签名为 prompt_fn(skill_name) -> ("allow", "deny", "always")
                      如果为 None，默认返回 False

        返回:
            bool: 是否可以执行
        """
        # 先检查是否已授权
        has_perm = self.has_permission(skill_name)
        if has_perm is not None:
            return has_perm

        # 首次使用，需要提示用户
        if prompt_fn is None:
            # 没有提供提示函数，默认拒绝
            return False

        # 调用提示函数
        choice = prompt_fn(skill_name)

        if choice == "allow":
            self.grant_permission(skill_name, always=False)
            return True
        elif choice == "always":
            self.grant_permission(skill_name, always=True)
            return True
        elif choice == "deny":
            self.deny_permission(skill_name)
            return False
        else:
            # 无效选择，默认拒绝
            return False

    def get_permission_status(self, skill_name: str) -> str:
        """
        获取技能的权限状态

        参数:
            skill_name: 技能名称

        返回:
            str: "allowed", "always", "denied", 或 "unknown"
        """
        # 先检查会话权限
        if skill_name in self.session_permissions:
            return self.session_permissions[skill_name]
        # 再检查永久权限
        return self.permissions.get(skill_name, "unknown")

    def list_permissions(self) -> dict:
        """
        列出所有权限配置（包括会话权限和永久权限）

        返回:
            dict: 权限字典的副本
        """
        # 合并会话权限和永久权限
        result = self.permissions.copy()
        result.update(self.session_permissions)
        return result
