"""
技能系统模块 - 提供可扩展的技能管理功能

核心组件:
    - models: 数据模型（Skill, Parameter, CodeBlock）
    - exceptions: 异常类（SkillNotFoundError, SkillValidationError, etc.）
    - parser: YAML+Markdown 解析器（即将实现）
    - loader: 技能文件加载器（即将实现）
    - inventory: 技能清单管理（即将实现）
    - executor: 技能执行引擎（即将实现）
    - permissions: 权限管理（即将实现）

使用示例:
    from pico.skills import Skill, SkillNotFoundError

    # 加载技能
    skill = load_skill("hello")

    # 调用技能
    try:
        result = invoke_skill("hello", name="World")
    except SkillNotFoundError as e:
        print(f"技能不存在: {e}")
"""

# 导出数据模型
from pico.skills.models import Skill, Parameter, CodeBlock

# 导出异常类
from pico.skills.exceptions import (
    SkillNotFoundError,
    SkillValidationError,
    SkillExecutionError,
    SkillPermissionDeniedError
)

# 定义公共 API
__all__ = [
    # 数据模型
    "Skill",
    "Parameter",
    "CodeBlock",
    # 异常类
    "SkillNotFoundError",
    "SkillValidationError",
    "SkillExecutionError",
    "SkillPermissionDeniedError",
]
