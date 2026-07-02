from pathlib import Path


def test_enterprise_ui_files_exist():
    assert Path("app/ui/app_enterprise.py").exists()
    assert Path("app/ui/components/navigation.py").exists()
    assert Path("app/ui/pages/enterprise_dashboard.py").exists()
