"""测试技能文件加载器"""
import os
import tempfile
from pathlib import Path

from pico.skills.loader import load_skills


def test_load_skills_empty_dir():
    """测试空目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills = load_skills(tmpdir)
        assert skills == []
        print("✅ 空目录测试通过")


def test_load_skills_nonexistent_dir():
    """测试不存在的目录"""
    skills = load_skills("/nonexistent/path/12345")
    assert skills == []
    print("✅ 不存在目录测试通过")


def test_load_skills_with_valid_files():
    """测试加载有效的技能文件"""
    project_root = Path(__file__).parent.parent.parent
    # 传入目录路径，不是文件路径
    skills_dir = project_root / ".pico" / "skills"
    skills = load_skills(str(skills_dir))
    assert len(skills) >= 1
    assert skills[0].name == "hello"
    print(f"✅ 加载测试通过: 加载了 {len(skills)} 个技能")


def test_load_skills_with_invalid_file():
    """测试跳过无效文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建一个无效的技能文件（缺少 name 字段）
        invalid_file = Path(tmpdir) / "invalid.md"
        invalid_file.write_text("---\ndescription: no name field\n---\nContent")

        # 创建一个有效的技能文件
        valid_file = Path(tmpdir) / "valid.md"
        valid_file.write_text("---\nname: valid\ndescription: A valid skill\n---\nContent")

        skills = load_skills(tmpdir)

        # 应该只加载有效的文件
        assert len(skills) == 1
        assert skills[0].name == "valid"
        print("✅ 无效文件跳过测试通过")


if __name__ == "__main__":
    test_load_skills_empty_dir()
    test_load_skills_nonexistent_dir()
    test_load_skills_with_valid_files()
    test_load_skills_with_invalid_file()
    print("\n✅ 所有 Loader 测试通过!")
