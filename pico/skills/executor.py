"""
技能执行器 - 提供 skill 的 prompt 指令

按照 Pi 的设计理念，skill 只提供 prompt 指令，AI 自己决定如何执行。
执行器不再自动执行代码，而是把 skill 内容作为 prompt 注入到对话中。

使用示例:
    from pico.skills.executor import SkillExecutor
    from pico.skills.permissions import SkillPermissions

    executor = SkillExecutor(permissions=SkillPermissions())

    # 执行技能
    result = executor.execute(skill, parameters={"name": "World"})
    print(result.prompt_injection)  # 注入到 prompt 的内容
"""
from dataclasses import dataclass
from typing import Dict, Optional

from pico.skills.models import Skill
from pico.skills.permissions import SkillPermissions


@dataclass
class ExecutionResult:
    """
    技能执行结果

    属性:
        success: 是否成功
        prompt_injection: 注入到 prompt 的内容
        code_output: 代码执行输出（保留字段，但不再使用）
        error_message: 错误信息（如果有）
        execution_time: 执行时间（秒）
    """
    success: bool
    prompt_injection: str = ""
    code_output: str = ""
    error_message: str = ""
    execution_time: float = 0.0


class SkillExecutor:
    """
    技能执行器

    按照 Pi 的设计理念，skill 只提供 prompt 指令，
    AI 根据指令自行决定使用哪些工具（包括 run_shell）来执行代码。

    属性:
        permissions: 权限管理器

    方法:
        execute(skill, parameters): 执行技能（返回 prompt 指令）
    """

    def __init__(self, permissions: Optional[SkillPermissions] = None, timeout: int = 30):
        """
        初始化执行器

        参数:
            permissions: 权限管理器（可选）
            timeout: 保留参数，向后兼容（不再使用）
        """
        self.permissions = permissions
        self.timeout = timeout  # 保留用于向后兼容

    def execute(self, skill: Skill, parameters: Optional[Dict[str, str]] = None, prompt_fn=None) -> ExecutionResult:
        """
        执行技能

        按照 Pi 的设计理念，skill 只提供 prompt 指令，AI 自己决定如何执行。
        无论 content_type 是什么，都只返回 prompt_injection。

        参数:
            skill: 要执行的技能
            parameters: 参数字典（保留用于向后兼容，但不再使用）
            prompt_fn: 权限提示函数

        返回:
            ExecutionResult: 执行结果（只包含 prompt_injection）
        """
        import time
        start_time = time.time()

        # 检查权限
        if self.permissions:
            if not self.permissions.check_permission(skill.name, prompt_fn=prompt_fn):
                return ExecutionResult(
                    success=False,
                    error_message=f"Permission denied for skill '{skill.name}'"
                )

        # 无论 content_type 是什么，都只返回 prompt_injection
        # 让 AI 自己决定如何使用这个指令
        prompt_injection = skill.content

        # 如果 skill 有 base_dir，添加详细的路径信息，方便 AI 引用辅助脚本
        if skill.base_dir:
            path_info = f"\n\n---\n"
            path_info += f"**Skill Location Info:**\n"
            path_info += f"- Base directory: `{skill.base_dir}`\n"
            path_info += f"- Helper scripts are in: `{skill.base_dir}/scripts/`\n"
            path_info += f"- When running scripts, use absolute paths:\n"
            path_info += f"  - Example: `python {skill.base_dir}/scripts/analyze_complexity.py <file_path>`\n"
            path_info += f"---\n"
            prompt_injection = path_info + prompt_injection

        result = ExecutionResult(
            success=True,
            prompt_injection=prompt_injection
        )

        result.execution_time = time.time() - start_time
        return result
