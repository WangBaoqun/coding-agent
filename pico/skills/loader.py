"""
技能文件加载器 - 扫描目录并批量加载技能文件

这个模块负责:
1. 扫描 .pico/skills/ 目录
2. 发现所有 .md 技能文件
3. 逐个解析技能文件
4. 跳过无效文件并记录警告
5. 返回 Skill 对象列表

使用示例:
    from pico.skills.loader import load_skills

    skills = load_skills(".pico/skills")
    print(f"加载了 {len(skills)} 个技能")
"""
import logging
from pathlib import Path
from typing import List

from pico.skills.models import Skill
from pico.skills.parser import parse_skill_file
from pico.skills.exceptions import SkillValidationError

logger = logging.getLogger(__name__)


def load_skills(skills_dir: str = ".pico/skills") -> List[Skill]:
    """
    从目录中加载所有技能文件

    支持两种 skill 组织方式：
    1. 单文件模式：skill 是一个 .md 文件（如 hello.md）
    2. 目录模式：skill 是一个目录，包含 skill.md 或 <dir-name>.md（如 code-review/skill.md）

    参数:
        skills_dir: 技能目录路径（默认 ".pico/skills"）

    返回:
        List[Skill]: 成功加载的技能列表

    行为:
        - 目录不存在 → 返回空列表
        - 目录为空 → 返回空列表
        - 文件解析失败 → 跳过该文件，记录警告，继续处理其他文件
        - 成功解析 → 添加到结果列表

    示例:
        skills = load_skills(".pico/skills")
        for skill in skills:
            print(f"{skill.name}: {skill.description}")
    """
    # 1. 检查目录是否存在
    dir_path = Path(skills_dir)
    if not dir_path.exists():
        logger.warning(f"技能目录不存在: {skills_dir}")
        return []

    if not dir_path.is_dir():
        logger.warning(f"路径不是目录: {skills_dir}")
        return []

    # 2. 扫描所有 .md 文件和子目录
    md_files = list(dir_path.glob("*.md"))
    subdirs = [d for d in dir_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

    if not md_files and not subdirs:
        logger.info(f"技能目录为空: {skills_dir}")
        return []

    logger.info(f"发现 {len(md_files)} 个技能文件和 {len(subdirs)} 个技能目录")

    # 3. 逐个解析
    skills = []

    # 3.1 解析单文件 skill
    for md_file in md_files:
        try:
            skill = parse_skill_file(str(md_file))
            skills.append(skill)
            logger.debug(f"成功加载技能: {skill.name}")
        except SkillValidationError as e:
            # 验证失败 → 记录警告，跳过
            logger.warning(f"跳过无效技能文件 {md_file}: {e}")
        except Exception as e:
            # 其他错误 → 记录警告，跳过
            logger.warning(f"解析技能文件失败 {md_file}: {e}")

    # 3.2 解析目录形式的 skill
    for subdir in subdirs:
        try:
            # 尝试查找 skill.md 或 <dir-name>.md
            skill_file = None
            if (subdir / "skill.md").exists():
                skill_file = subdir / "skill.md"
            elif (subdir / f"{subdir.name}.md").exists():
                skill_file = subdir / f"{subdir.name}.md"

            if skill_file is None:
                logger.debug(f"跳过目录 {subdir}: 未找到 skill.md 或 {subdir.name}.md")
                continue

            # 解析 skill，传入 subdir 作为 base_dir
            skill = parse_skill_file(str(skill_file), base_dir=str(subdir))
            skills.append(skill)
            logger.debug(f"成功加载技能: {skill.name} (from {subdir})")
        except SkillValidationError as e:
            # 验证失败 → 记录警告，跳过
            logger.warning(f"跳过无效技能目录 {subdir}: {e}")
        except Exception as e:
            # 其他错误 → 记录警告，跳过
            logger.warning(f"解析技能目录失败 {subdir}: {e}")

    logger.info(f"成功加载 {len(skills)}/{len(md_files) + len(subdirs)} 个技能")
    return skills
