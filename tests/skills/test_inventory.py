"""测试技能清单管理器"""
import tempfile
from pathlib import Path
from pico.skills.models import Skill, Parameter, CodeBlock
from pico.skills.inventory import SkillsInventory
from pico.skills.loader import load_skills


def create_test_skill(name: str, description: str, category: str = "") -> Skill:
    """创建测试用的 Skill 对象"""
    return Skill(
        name=name,
        description=description,
        category=category,
        parameters=[],
        content="",
        content_type="prompt_only",
        code_blocks=[],
        file_path=f".pico/skills/{name}.md"
    )


def test_empty_inventory():
    """测试空清单"""
    inv = SkillsInventory([])

    # 空清单应该返回空字符串
    assert inv.render() == ""
    assert inv.token_count() == 0
    assert len(inv.skills) == 0

    print("✅ 空清单测试通过")


def test_single_skill():
    """测试单个技能"""
    skill = create_test_skill("hello", "A greeting skill", "demo")
    inv = SkillsInventory([skill])

    # 验证清单格式
    rendered = inv.render()
    assert "Available Skills" in rendered
    assert "hello: A greeting skill" in rendered
    assert "/skill:hello" in rendered

    # 验证 token 计数（10 + 1*6 = 16）
    assert inv.token_count() == 16

    print("✅ 单个技能测试通过")


def test_multiple_skills_sorted():
    """测试多个技能按名称排序"""
    skill1 = create_test_skill("zebra", "Z skill")
    skill2 = create_test_skill("alpha", "A skill")
    skill3 = create_test_skill("middle", "M skill")

    inv = SkillsInventory([skill1, skill2, skill3])

    # 验证排序
    assert inv.skills[0].name == "alpha"
    assert inv.skills[1].name == "middle"
    assert inv.skills[2].name == "zebra"

    # 验证清单中的顺序
    rendered = inv.render()
    alpha_pos = rendered.find("alpha")
    middle_pos = rendered.find("middle")
    zebra_pos = rendered.find("zebra")
    assert alpha_pos < middle_pos < zebra_pos

    # 验证 token 计数（10 + 3*6 = 28）
    assert inv.token_count() == 28

    print("✅ 多个技能排序测试通过")


def test_token_count():
    """测试 token 计数"""
    # 0 个技能
    inv0 = SkillsInventory([])
    assert inv0.token_count() == 0

    # 1 个技能
    inv1 = SkillsInventory([create_test_skill("test1", "desc1")])
    assert inv1.token_count() == 16  # 10 + 1*6

    # 5 个技能
    skills = [create_test_skill(f"skill{i}", f"desc{i}") for i in range(5)]
    inv5 = SkillsInventory(skills)
    assert inv5.token_count() == 40  # 10 + 5*6

    # 100 个技能
    skills100 = [create_test_skill(f"skill{i}", f"desc{i}") for i in range(100)]
    inv100 = SkillsInventory(skills100)
    assert inv100.token_count() == 610  # 10 + 100*6

    print("✅ Token 计数测试通过")


def test_filter_by_category():
    """测试按分类过滤"""
    skill1 = create_test_skill("code-review", "Review code", "code")
    skill2 = create_test_skill("hello", "Greeting", "demo")
    skill3 = create_test_skill("test-gen", "Generate tests", "testing")
    skill4 = create_test_skill("lint", "Lint code", "code")

    inv = SkillsInventory([skill1, skill2, skill3, skill4])

    # 过滤 code 分类
    code_inv = inv.filter_by_category("code")
    assert len(code_inv.skills) == 2
    assert code_inv.skills[0].name == "code-review"
    assert code_inv.skills[1].name == "lint"

    # 过滤 demo 分类
    demo_inv = inv.filter_by_category("demo")
    assert len(demo_inv.skills) == 1
    assert demo_inv.skills[0].name == "hello"

    # 过滤不存在的分类
    empty_inv = inv.filter_by_category("nonexistent")
    assert len(empty_inv.skills) == 0
    assert empty_inv.render() == ""

    print("✅ 分类过滤测试通过")


def test_search():
    """测试关键词搜索"""
    skill1 = create_test_skill("code-review", "Review code for bugs")
    skill2 = create_test_skill("hello", "A greeting skill")
    skill3 = create_test_skill("test-gen", "Generate unit tests")

    inv = SkillsInventory([skill1, skill2, skill3])

    # 搜索 "code"（匹配 name 和 description）
    code_results = inv.search("code")
    assert len(code_results.skills) == 1  # code-review （name 和 description 中有 tests）
    assert code_results.skills[0].name == "code-review"

    # 搜索 "greeting"（只匹配 description）
    greeting_results = inv.search("greeting")
    assert len(greeting_results.skills) == 1
    assert greeting_results.skills[0].name == "hello"

    # 不区分大小写
    upper_results = inv.search("CODE")
    assert len(upper_results.skills) == len(code_results.skills)

    # 搜索不存在的关键词
    no_results = inv.search("nonexistent")
    assert len(no_results.skills) == 0

    print("✅ 关键词搜索测试通过")


def test_combined_operations():
    """测试组合操作"""
    skill1 = create_test_skill("code-review", "Review code", "code")
    skill2 = create_test_skill("hello", "Greeting", "demo")
    skill3 = create_test_skill("code-lint", "Lint code", "code")

    inv = SkillsInventory([skill1, skill2, skill3])

    # 先过滤再搜索
    code_inv = inv.filter_by_category("code")
    review_results = code_inv.search("review")

    assert len(review_results.skills) == 1
    assert review_results.skills[0].name == "code-review"

    print("✅ 组合操作测试通过")


def test_reload_no_changes():
    """测试重新加载没有变化的目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建一个技能文件
        skill_file = Path(tmpdir) / "test.md"
        skill_file.write_text("---\nname: test\ndescription: Test skill\n---\nContent")

        # 创建 SkillsInventory
        skills = load_skills(tmpdir)
        inv = SkillsInventory(skills)
        assert len(inv.skills) == 1

        # 重新加载（没有变化）
        result = inv.reload(tmpdir)

        # 断言：added=[], removed=[], updated=["test"]
        assert result["added"] == []
        assert result["removed"] == []
        assert result["updated"] == ["test"]

    print("✅ 重新加载无变化测试通过")


def test_reload_add_skill():
    """测试添加新技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建第一个技能文件
        skill1_file = Path(tmpdir) / "skill1.md"
        skill1_file.write_text("---\nname: skill1\ndescription: Skill 1\n---\nContent 1")

        # 创建 SkillsInventory
        skills = load_skills(tmpdir)
        inv = SkillsInventory(skills)
        assert len(inv.skills) == 1

        # 添加第二个技能文件
        skill2_file = Path(tmpdir) / "skill2.md"
        skill2_file.write_text("---\nname: skill2\ndescription: Skill 2\n---\nContent 2")

        # 重新加载
        result = inv.reload(tmpdir)

        # 断言：added=["skill2"], removed=[], updated=["skill1"]
        assert "skill2" in result["added"]
        assert result["removed"] == []
        assert "skill1" in result["updated"]

        # 验证清单已更新
        assert len(inv.skills) == 2

    print("✅ 添加新技能测试通过")


def test_reload_remove_skill():
    """测试删除技能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建两个技能文件
        skill1_file = Path(tmpdir) / "skill1.md"
        skill1_file.write_text("---\nname: skill1\ndescription: Skill 1\n---\nContent 1")

        skill2_file = Path(tmpdir) / "skill2.md"
        skill2_file.write_text("---\nname: skill2\ndescription: Skill 2\n---\nContent 2")

        # 创建 SkillsInventory
        skills = load_skills(tmpdir)
        inv = SkillsInventory(skills)
        assert len(inv.skills) == 2

        # 删除一个技能文件
        skill2_file.unlink()

        # 重新加载
        result = inv.reload(tmpdir)

        # 断言：added=[], removed=["skill2"], updated=["skill1"]
        assert result["added"] == []
        assert "skill2" in result["removed"]
        assert "skill1" in result["updated"]

        # 验证清单已更新
        assert len(inv.skills) == 1
        assert inv.skills[0].name == "skill1"

    print("✅ 删除技能测试通过")


if __name__ == "__main__":
    test_empty_inventory()
    test_single_skill()
    test_multiple_skills_sorted()
    test_token_count()
    test_filter_by_category()
    test_search()
    test_combined_operations()
    test_reload_no_changes()
    test_reload_add_skill()
    test_reload_remove_skill()
    print("\n✅ 所有 Inventory 测试通过!")
