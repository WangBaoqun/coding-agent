"""
技能清单管理器 - 生成轻量清单用于 prompt 注入

这个模块负责:
1. 管理技能列表
2. 生成轻量清单文本（用于注入到 prompt）
3. 计算 token 数量（确保 < 5% prompt 预算）
4. 支持按分类过滤
5. 支持关键词搜索

使用示例:
    from pico.skills.inventory import SkillsInventory
    from pico.skills.loader import load_skills

    skills = load_skills(".pico/skills")
    inventory = SkillsInventory(skills)

    # 生成清单文本
    text = inventory.render()
    print(text)

    # 按分类过滤
    code_skills = inventory.filter_by_category("code")

    # 按关键词搜索
    results = inventory.search("review")
"""
from typing import List
from pico.skills.models import Skill
from pico.skills.loader import load_skills


class SkillsInventory:
    """
    技能清单管理器

    属性:
        skills: 技能列表（按名称排序）

    方法:
        render(): 生成清单文本
        filter_by_category(category): 按分类过滤
        search(keyword): 按关键词搜索
        token_count(): 计算 token 数量
    """

    def __init__(self, skills: List[Skill]):
        """
        初始化清单

        参数:
            skills: 技能列表
        """
        # 按名称排序并保存
        self.skills = sorted(skills, key=lambda skill: skill.name)

    def render(self) -> str:
        """
        生成清单文本（用于 prompt 注入）

        采用 Pi 的设计风格：使用 XML 标签展示技能信息，
        引导模型在任务匹配时自主使用 read_file 工具加载技能。

        返回:
            str: 清单文本

        格式示例:
            <available_skills>
            IMPORTANT: When you read a skill file, you MUST follow ALL instructions in it,
            including running any helper scripts mentioned. Do not skip required steps.

            <skill>
              <name>hello</name>
              <description>A simple greeting skill</description>
              <location>.pico/skills/hello/SKILL.md</location>
            </skill>
            </available_skills>
        """
        if not self.skills:
            return ""

        lines = [
            "<available_skills>",
            "IMPORTANT: When you read a skill file, you MUST follow ALL instructions in it,",
            "including running any helper scripts mentioned. Do not skip required steps.",
            "",
        ]

        for skill in self.skills:
            lines.append("<skill>")
            lines.append(f"  <name>{skill.name}</name>")
            lines.append(f"  <description>{skill.description}</description>")
            lines.append(f"  <location>{skill.file_path}</location>")
            lines.append("</skill>")

        lines.append("</available_skills>")
        return "\n".join(lines)

    def filter_by_category(self, category: str) -> 'SkillsInventory':
        """
        按分类过滤

        参数:
            category: 分类名称

        返回:
            SkillsInventory: 新的清单对象（只包含匹配的技能）
        """
        # 按照 category 过滤技能
        filtered_skills = [skill for skill in self.skills if skill.category == category]
        return SkillsInventory(filtered_skills)

    def search(self, keyword: str) -> 'SkillsInventory':
        """
        按关键词搜索（匹配 name 或 description）

        参数:
            keyword: 搜索关键词

        返回:
            SkillsInventory: 新的清单对象（只包含匹配的技能）
        """
        # 按关键词搜索技能
        keyword_lower = keyword.lower()
        matched_skills = [
            skill for skill in self.skills
            if keyword_lower in skill.name.lower()
            or keyword_lower in skill.description.lower()]
        return SkillsInventory(matched_skills)

    def token_count(self) -> int:
        """
        计算清单占用的 token 数量

        返回:
            int: token 数量

        估算规则:
            - 每个技能约 5-6 个 token
            - 标题行约 10 个 token
        """
        # 计算 token 数量
        if not self.skills:
            return 0
        # 标题 10 tokens + 每个技能 6 tokens
        return 10 + len(self.skills) * 6

    def reload(self, skills_dir: str) -> dict:
        """
        重新加载技能清单

        参数:
            skills_dir: 技能目录路径

        返回:
            dict: 包含 added, removed, updated 三个列表
        """
        # 旧技能列表
        old_skills = self.skills
        old_set = {old_skill.name for old_skill in old_skills}

        # 新加载的技能
        new_skills = load_skills(skills_dir)
        new_set = {new_skill.name for new_skill in new_skills}

        # 计算变化
        added = new_set - old_set
        removed = old_set - new_set
        updated = old_set & new_set

        # 更新技能
        self.skills = sorted(new_skills, key=lambda skill: skill.name)

        return {"added": list(added), "removed": list(removed), "updated": list(updated)}