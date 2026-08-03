"""测试技能文件解析器"""
from pathlib import Path
from pico.skills.parser import parse_skill_file


def test_parse_hello_skill():
    """测试解析 hello.md 技能文件"""
    # 使用项目根目录的相对路径
    project_root = Path(__file__).parent.parent.parent
    skill_path = project_root / ".pico" / "skills" / "hello.md"

    skill = parse_skill_file(str(skill_path))

    # 验证元数据
    assert skill.name == "hello"
    assert skill.description == "A simple greeting skill"
    assert skill.category == "demo"

    # 验证参数
    assert len(skill.parameters) == 1
    param = skill.parameters[0]
    assert param.name == "name"
    assert param.type == "string"
    assert param.required == False
    assert param.default == "World"

    # 验证内容类型（有文本也有代码块，应该是 hybrid）
    assert skill.content_type == "hybrid"

    # 验证代码块
    assert len(skill.code_blocks) == 1
    code_block = skill.code_blocks[0]
    assert code_block.language == "python"
    assert "print" in code_block.code
    assert code_block.index == 0

    # 验证文件路径（现在是绝对路径）
    assert skill.file_path == str(skill_path)
    assert skill.file_path.endswith("hello.md")

    # 验证正文内容
    assert "# Hello Skill" in skill.content
    assert "{name}" in skill.content

    print("✅ 所有测试通过!")
    print(f"\n解析结果:")
    print(f"  名称: {skill.name}")
    print(f"  描述: {skill.description}")
    print(f"  分类: {skill.category}")
    print(f"  类型: {skill.content_type}")
    print(f"  参数: {[p.name for p in skill.parameters]}")
    print(f"  代码块: {[(cb.language, cb.index) for cb in skill.code_blocks]}")


if __name__ == "__main__":
    test_parse_hello_skill()
