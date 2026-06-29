import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class SchemaAuthoringGuidelinesTest(unittest.TestCase):
    def test_mcp_projectable_schemas_do_not_use_composition_keywords(self) -> None:
        """Schemas under schemas/ are treated as MCP-projectable in this repo."""
        forbidden = {"oneOf", "anyOf", "allOf"}
        findings: list[str] = []

        for schema_path in sorted((REPO_ROOT / "schemas").glob("*.schema.json")):
            schema = json.loads(schema_path.read_text())

            def walk(node: object, path: str) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        next_path = f"{path}/{key}"
                        if key in forbidden:
                            findings.append(f"{schema_path.relative_to(REPO_ROOT)}:{next_path}")
                        walk(value, next_path)
                elif isinstance(node, list):
                    for index, value in enumerate(node):
                        walk(value, f"{path}/{index}")

            walk(schema, "")

        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
