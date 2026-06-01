from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from oauth_openai_compat_server import CompatHandler


ROOT = Path(__file__).resolve().parents[1]
DOCS = ["README.md", "USABLE_OAUTH_METHODS.md"]


def normalize(route: str) -> str:
    return route.split(" ", 1)[1] if route.startswith("OPTIONS ") else route


def server_main_routes() -> list[str]:
    source = (ROOT / "src" / "oauth_openai_compat_server.py").read_text()
    module = ast.parse(source)
    route_lists: list[list[str]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Dict(self, node: ast.Dict) -> None:
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "routes"
                    and isinstance(value, ast.List)
                ):
                    route_lists.append([
                        item.value
                        for item in value.elts
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    ])
            self.generic_visit(node)

    Visitor().visit(module)
    if not route_lists:
        raise RuntimeError("Could not find main() routes list in oauth_openai_compat_server.py")
    return route_lists[-1]


def capability_routes() -> list[str]:
    fake = SimpleNamespace(
        router=SimpleNamespace(
            oauth=SimpleNamespace(
                model_ids=["gpt-5.5"],
                discovered_model_ids=["gpt-5.5"],
                model_probe_error=None,
            )
        )
    )
    payload = CompatHandler.capabilities_payload(fake)
    routes: list[str] = []
    for group in ("local_openai_compatible_proxy", "local_extension_routes"):
        group_routes = payload.get(group)
        if not isinstance(group_routes, list):
            raise RuntimeError(f"capabilities payload missing route group: {group}")
        routes.extend(route for route in group_routes if isinstance(route, str))
    return routes


def docs_text() -> str:
    return "\n".join((ROOT / name).read_text() for name in DOCS)


def main() -> int:
    main_routes = server_main_routes()
    cap_routes = capability_routes()
    main_set = {normalize(route) for route in main_routes}
    cap_set = {normalize(route) for route in cap_routes}
    missing_in_main = sorted(cap_set - main_set)
    extra_in_main = sorted(main_set - cap_set)
    text = docs_text()
    missing_in_docs = sorted(route for route in cap_routes if route not in text)

    if missing_in_main or extra_in_main or missing_in_docs:
        print("Route manifest verification failed.")
        if missing_in_main:
            print("missing_in_main:")
            for route in missing_in_main:
                print(f"  {route}")
        if extra_in_main:
            print("extra_in_main:")
            for route in extra_in_main:
                print(f"  {route}")
        if missing_in_docs:
            print("missing_in_docs:")
            for route in missing_in_docs:
                print(f"  {route}")
        return 1

    print(
        f"Route manifest verification passed: "
        f"{len(cap_routes)} capability routes match server main output and docs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
