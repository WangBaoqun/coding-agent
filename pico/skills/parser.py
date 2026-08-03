"""
技能文件解析器 - 解析 YAML+Markdown 格式的技能文件

这个模块负责:
1. 读取技能文件（.md 格式）
2. 解析 YAML frontmatter（元数据）
3. 解析 Markdown 正文（内容和代码块）
4. 验证必填字段
5. 构建 Skill 对象

使用示例:
    from pico.skills.parser import parse_skill_file

    skill = parse_skill_file(".pico/skills/hello.md")
    print(skill.name)  # "hello"
"""
from pathlib import Path
from typing import List
import re

import frontmatter
from markdown_it import MarkdownIt

from pico.skills.models import Skill, Parameter, CodeBlock
from pico.skills.exceptions import SkillValidationError


def parse_skill_file(file_path: str) -> Skill:
    """
    解析技能文件并返回 Skill 对象

    参数:
        file_path: 技能文件路径（如 ".pico/skills/hello.md"）

    返回:
        Skill: 解析后的技能对象

    异常:
        SkillValidationError: 文件格式错误或验证失败

    示例:
        skill = parse_skill_file(".pico/skills/hello.md")
    """

    # frontmatter.load() 返回一个 Post 对象
    post = frontmatter.load(file_path)

    # post.metadata 是 YAML 字典
    metadata = post.metadata

    # 验证元数据
    validate_skill_metadata(metadata, file_path)

    # 解析参数
    parameters = parse_parameters(metadata.get("parameters", []))

    # 提取代码块
    content = post.content
    code_blocks = extract_code_blocks(content)

    # 检测内容类型
    content_type = detect_content_type(content, code_blocks)

    skill = Skill(
        name=metadata["name"],
        description=metadata["description"],
        category=metadata.get("category", ""),
        parameters=parameters,
        content=content,
        content_type=content_type,
        code_blocks=code_blocks,
        file_path=str(file_path),
    )

    return skill


def extract_code_blocks(content: str) -> List[CodeBlock]:
    """
    从 Markdown 内容中提取代码块

    参数:
        content: Markdown 正文内容

    返回:
        List[CodeBlock]: 代码块列表

    示例:
        content = '''
        Some text

        ```python
        print("hello")
        ```
        '''
        blocks = extract_code_blocks(content)
        # [CodeBlock(language="python", code='print("hello")', index=0)]
    """

    # 1. 创建 Markdown 解析器实例
    md = MarkdownIt()

    # 2. 将 Markdown 内容解析为 tokens 列表
    # tokens 是 Markdown 的各种元素（段落、标题、代码块等）
    tokens = md.parse(content)

    # 3. 遍历 tokens，提取代码块
    code_blocks = []
    code_block_index = 0  # 代码块的序号（从 0 开始）

    for token in tokens:
        # 代码块在 markdown-it 中的类型是 "fence"
        if token.type == "fence":
            # 创建 CodeBlock 对象
            code_block = CodeBlock(
                language=token.info.strip(),  # 语言标记（如 "python", "bash"）
                code=token.content,           # 代码内容
                index=code_block_index        # 代码块序号（不是 token 的位置）
            )
            code_blocks.append(code_block)
            code_block_index += 1  # 递增代码块计数器

    return code_blocks


def detect_content_type(content: str, code_blocks: List[CodeBlock]) -> str:
    """
    检测技能内容类型

    参数:
        content: Markdown 正文内容
        code_blocks: 代码块列表

    返回:
        str: "prompt_only", "code_only", 或 "hybrid"

    规则:
        - 只有文本，无代码块 → "prompt_only"
        - 只有代码块，无文本 → "code_only"
        - 两者都有 → "hybrid"
    """

    has_content = bool(content.strip())  # 是否有文本内容
    has_code = len(code_blocks) > 0      # 是否有代码块

    if has_content and has_code:
        return "hybrid"
    elif has_content:
        return "prompt_only"
    elif has_code:
        return "code_only"
    else:
        # 理论上不应该到达这里（验证会提前捕获）
        return "prompt_only"


def validate_skill_metadata(metadata: dict, file_path: str) -> None:
    """
    验证技能元数据（YAML frontmatter）

    参数:
        metadata: 解析后的 YAML 字典
        file_path: 文件路径（用于错误消息）

    异常:
        SkillValidationError: 验证失败时抛出

    验证规则:
        - name: 必填，1-50字符，只能包含字母、数字、连字符
        - description: 必填，最大100字符
        - category: 可选
        - parameters: 可选，但格式必须正确
    """
    # 处理 metadata 为 None 的情况
    if metadata is None:
        raise SkillValidationError(file_path, ["元数据为空"])

    errors = []

    # 验证 name 字段
    if "name" not in metadata:
        errors.append("缺少必填字段: name")
    elif not isinstance(metadata["name"], str):
        errors.append("name 必须是字符串")
    else:
        name = metadata["name"]
        # 检查长度（使用 or 而不是 and）
        if len(name) == 0 or len(name) > 50:
            errors.append(f"name 长度必须在 1-50 字符之间（当前: {len(name)}）")

        # 正则表达式：^ 开头，[a-zA-Z0-9-]+ 一个或多个字母数字连字符，$ 结尾
        if not re.match(r'^[a-zA-Z0-9-]+$', name):
            errors.append(f"name 只能包含字母、数字和连字符: {name}")

    # 验证 description 字段
    if "description" not in metadata:
        errors.append("缺少必填字段: description")
    elif not isinstance(metadata["description"], str):
        errors.append("description 必须是字符串")
    elif len(metadata["description"]) > 100:
        errors.append(f"description 超过 100 字符（当前: {len(metadata['description'])}）")

    # 如果有错误，抛出异常
    if errors:
        raise SkillValidationError(file_path, errors)


def parse_parameters(params_data: list) -> List[Parameter]:
    """
    解析参数定义列表

    参数:
        params_data: YAML 中的参数列表

    返回:
        List[Parameter]: Parameter 对象列表

    示例:
        params_data = [
            {"name": "file_path", "type": "string", "required": True},
            {"name": "count", "type": "int", "required": False, "default": 10}
        ]
        params = parse_parameters(params_data)
    """

    if not params_data:  # 处理 None 和空列表
        return []

    result: list = []
    for param_dict in params_data:
        # 提取必填字段
        name = param_dict.get("name")
        type = param_dict.get("type")
        required = param_dict.get("required")

        # 提取可选字段
        description = param_dict.get("description", "")
        default = param_dict.get("default", None)

        # 创建 Parameter 对象
        param = Parameter(
            name=name,
            type=type,
            required=required,
            description=description,
            default=default,
        )

        result.append(param)

    return result
