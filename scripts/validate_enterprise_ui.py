from __future__ import annotations

from pathlib import Path


def main() -> None:
    required = [
        "app/ui/app_enterprise.py",
        "app/ui/components/navigation.py",
        "app/ui/components/header.py",
        "app/ui/components/cards.py",
        "app/ui/pages/enterprise_dashboard.py",
        "app/ui/pages/advisor_360.py",
        "app/ui/pages/agp_goals_coaching.py",
    ]
    for file in required:
        assert Path(file).exists(), f"Missing {file}"
    print("Streamlit Enterprise UI validation passed.")
    print("Run: uv run streamlit run app/ui/app_enterprise.py")


if __name__ == "__main__":
    main()
