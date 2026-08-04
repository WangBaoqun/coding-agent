"""
数据模型定义 - 技能系统的核心数据结构

这个模块定义了技能系统使用的所有数据类：
- Parameter: 技能参数定义
- CodeBlock: 可执行代码块
- Skill: 完整的技能定义
"""
from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class Parameter:
    """
    技能参数定义

    属性:
        name: 参数名称（字母、数字、下划线）
        type: 参数类型（string, int, float, bool）
        required: 是否必填
        description: 参数描述（可选）
        default: 默认值（可选，类型必须匹配 type 字段）

    示例:
        Parameter(name="file_path", type="string", required=True)
        Parameter(name="count", type="int", required=False, default=10)
    """
    name: str
    type: str
    required: bool
    description: str = ""  # 可选，默认为空字符串
    default: Any = None    # 可以是任何类型，默认为 None


@dataclass
class CodeBlock:
    """
    技能中的可执行代码块

    属性:
        language: 编程语言（如 python, bash, shell）
        code: 代码内容
        index: 在 Markdown 正文中的位置（从 0 开始）

    用途:
        系统会提取这些代码块并执行（仅支持 python 和 bash/shell）
    """
    language: str  # 编程语言
    code: str      # 代码内容
    index: int     # 在 skill 文档中的位置（第几个代码块）


@dataclass
class Skill:
    """
    技能定义 - 系统的核心实体

    属性:
        name: 技能唯一标识符（如 "code-review", "hello"）
        description: 技能简短描述（显示在清单中）
        category: 技能分类（如 "code", "testing", "demo"）
        parameters: 参数定义列表
        content: Markdown 正文内容（Prompt 指令）
        content_type: 内容类型（prompt_only, code_only, hybrid）
        code_blocks: 提取的代码块列表
        file_path: 技能文件的完整路径
        base_dir: 技能文件所在目录（用于解析相对路径的辅助脚本）

    内容类型说明:
        - prompt_only: 仅包含 Prompt 指令，无代码块
        - code_only: 仅包含代码块，无 Prompt 指令
        - hybrid: 同时包含 Prompt 指令和代码块

    示例:
        skill = Skill(
            name="hello",
            description="A greeting skill",
            category="demo",
            parameters=[Parameter(name="name", type="string", required=False)],
            content="# Hello\\nSay hello to {name}",
            content_type="prompt_only",
            code_blocks=[],
            file_path=".pico/skills/hello.md",
            base_dir=".pico/skills"
        )
    """
    name: str
    description: str
    category: str = ""  # 可选分类
    parameters: List[Parameter] = field(default_factory=list)  # 避免共享可变对象
    content: str = ""   # Markdown 正文
    content_type: str = "prompt_only"  # 默认类型
    code_blocks: List[CodeBlock] = field(default_factory=list)
    file_path: str = ""  # 文件路径
    base_dir: str = ""  # 技能文件所在目录（用于解析辅助脚本的相对路径）
