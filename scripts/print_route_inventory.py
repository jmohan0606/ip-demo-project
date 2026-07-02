from __future__ import annotations

from app.api.main import app


def main() -> None:
    print("API Route Inventory")
    for route in sorted(app.routes, key=lambda r: getattr(r, "path", "")):
        methods = ",".join(sorted(getattr(route, "methods", []) or []))
        print(f"{methods:12s} {getattr(route, 'path', '')}")


if __name__ == "__main__":
    main()
