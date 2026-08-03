"""
异常类定义 - 技能系统的错误处理

这个模块定义了技能系统可能抛出的所有自定义异常。
每个异常都继承自 Exception 基类，并添加了有用的上下文信息。

使用场景:
    - SkillNotFoundError: 尝试调用不存在的技能
    - SkillValidationError: 技能文件格式错误或验证失败
    - SkillExecutionError: 技能执行过程中发生错误
    - SkillPermissionDeniedError: 用户拒绝执行技能

示例:
    try:
        skill = load_skill("nonexistent")
    except SkillNotFoundError as e:
        print(f"错误: {e}")
        print(f"建议: {e.suggestions}")
"""


class SkillNotFoundError(Exception):
    """
    技能不存在异常

    当用户尝试调用一个不存在的技能时抛出。

    属性:
        skill_name: 用户尝试调用的技能名称
        available_skills: 当前可用的技能列表（用于提供建议）
        message: 错误消息

    示例:
        raise SkillNotFoundError(
            skill_name="code-reviews",
            available_skills=["code-review", "hello", "generate-tests"]
        )
    """

    def __init__(self, skill_name: str, available_skills: list = None):
        """
        初始化异常

        Args:
            skill_name: 不存在的技能名称
            available_skills: 可用技能列表（可选）
        """
        self.skill_name = skill_name
        self.available_skills = available_skills or []
        self.suggestions = self._find_similar_skills()

        # 构建错误消息
        message = f"技能 '{skill_name}' 不存在"
        if self.suggestions:
            message += f"。你是否想要: {', '.join(self.suggestions)}?"

        super().__init__(message)

    def _find_similar_skills(self) -> list:
        """
        查找名称相似的技能（简单的字符串匹配）

        Returns:
            相似技能名称列表（最多3个）
        """
        if not self.available_skills:
            return []

        # 简单的相似度检查：包含关系或前缀匹配
        similar = []
        for skill in self.available_skills:
            # 如果输入的技能名是现有技能的子串，或者反过来
            if (self.skill_name in skill or skill in self.skill_name):
                similar.append(skill)
            # 或者前3个字符相同
            elif len(self.skill_name) >= 3 and skill.startswith(self.skill_name[:3]):
                similar.append(skill)

        return similar[:3]  # 最多返回3个建议


class SkillValidationError(Exception):
    """
    技能验证失败异常

    当技能文件格式错误或必填字段缺失时抛出。

    属性:
        file_path: 技能文件路径
        validation_errors: 验证错误列表
        message: 错误消息

    示例:
        raise SkillValidationError(
            file_path=".pico/skills/invalid.md",
            validation_errors=["缺少必填字段: name", "description 超过100字符"]
        )
    """

    def __init__(self, file_path: str, validation_errors: list):
        """
        初始化异常

        Args:
            file_path: 技能文件路径
            validation_errors: 验证错误列表
        """
        self.file_path = file_path
        self.validation_errors = validation_errors

        # 构建详细的错误消息
        errors_str = "\n  - ".join(validation_errors)
        message = f"技能文件验证失败: {file_path}\n错误详情:{errors_str}"

        super().__init__(message)


class SkillExecutionError(Exception):
    """
    技能执行失败异常

    当技能执行过程中发生错误时抛出（如代码执行失败、超时等）。

    属性:
        skill_name: 技能名称
        original_error: 原始异常（可选）
        execution_context: 执行上下文信息（可选）
        message: 错误消息

    示例:
        try:
            result = execute_code("print(1/0)")
        except ZeroDivisionError as e:
            raise SkillExecutionError(
                skill_name="run-python",
                original_error=e,
                execution_context={"code": "print(1/0)"}
            )
    """

    def __init__(
        self,
        skill_name: str,
        original_error: Exception = None,
        execution_context: dict = None
    ):
        """
        初始化异常

        Args:
            skill_name: 技能名称
            original_error: 原始异常（可选）
            execution_context: 执行上下文信息（可选）
        """
        self.skill_name = skill_name
        self.original_error = original_error
        self.execution_context = execution_context or {}

        # 构建错误消息
        message = f"技能 '{skill_name}' 执行失败"

        if original_error:
            message += f": {type(original_error).__name__}: {original_error}"

        if execution_context:
            message += f"\n执行上下文: {execution_context}"

        super().__init__(message)


class SkillPermissionDeniedError(Exception):
    """
    技能权限被拒绝异常

    当用户拒绝执行技能时抛出。

    属性:
        skill_name: 技能名称
        reason: 拒绝原因（可选）
        message: 错误消息

    示例:
        raise SkillPermissionDeniedError(
            skill_name="dangerous-skill",
            reason="用户选择拒绝执行"
        )
    """

    def __init__(self, skill_name: str, reason: str = ""):
        """
        初始化异常

        Args:
            skill_name: 技能名称
            reason: 拒绝原因（可选）
        """
        self.skill_name = skill_name
        self.reason = reason

        # 构建错误消息
        message = f"技能 '{skill_name}' 的执行被拒绝"
        if reason:
            message += f": {reason}"

        message += "\n提示: 你可以通过权限管理界面更改此设置"

        super().__init__(message)
