# MCP And MCPB Authoring Guide

## Purpose

Use this guide when designing MCP servers, MCP tool definitions, MCPB packages,
Claude-compatible tool surfaces, or repository JSON schemas intended to be
projected into those surfaces. The goal is to keep tool-facing schemas portable
across MCP hosts and LLM tool adapters while avoiding composition forms that are
hard to project into tool contracts.

This repository treats `schemas/*.schema.json` as MCP-projectable artifact
contracts unless a schema is explicitly documented as internal-only. For
MCP-projectable schemas, use the same schema-shape discipline as MCP/MCPB
tool-facing contracts. Internal-only schemas may use JSON Schema composition
when it materially reduces complexity, but expose them through an explicit
adapter or projection boundary before they reach an MCP/Claude tool surface.

## Compatibility Baseline

- Treat the MCP specification as the protocol baseline and Claude tool-use rules
  as a practical strict compatibility target for Claude Desktop, Claude Code,
  and Claude-backed MCPB hosts.
- Validate MCPB manifests with the current MCPB manifest schema or packaging
  command before release.
- Validate each MCP tool definition separately from the MCPB manifest. A package
  can be structurally valid while a Claude host still rejects a tool name or
  tool `input_schema`.
- Prefer the smallest compatible schema surface and move complex validation into
  deterministic code or server-side dispatch.

## Naming Rules

Use one canonical tool name everywhere: MCP catalog, server dispatch, audit logs,
allowed-tool configuration, docs, and examples.

Recommended pattern:

```text
namespace_verb
```

Examples:

```text
sheets_read
sheets_apply
workbook_inspect
workbook_validate
package_create
```

Rules:

- Match Claude-compatible tool names: `^[a-zA-Z0-9_-]{1,64}$`.
- Use lowercase `snake_case` for tool names even though the regex allows more.
- Do not use dots in tool names. Use `sheets_read`, not `sheets.read`.
- Do not use spaces, slashes, colons, path-like names, or display labels as tool
  names.
- Keep input property names lowercase `snake_case`.
- Do not use dots in user-facing config keys or tool input property names. Use
  `client_id`, not `client.id`.
- Keep display names human-friendly in manifest/UI metadata, not in tool names.

Reasoning:

- MCP allows a broader tool-name character set than Claude tool definitions.
- Claude tool names are a stricter host contract. Designing to that stricter
  contract avoids host-specific renaming, audit mismatches, and adapter failures.

## JSON Schema Shape Rules

Every MCP tool `input_schema` should be a direct object schema.
MCP-projectable artifact schemas should use the same explicit object style
unless a schema is owned by an external standard.

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["inspect", "apply"]
    },
    "target_range": {
      "type": "string"
    }
  },
  "required": ["operation"],
  "additionalProperties": false
}
```

Rules:

- Put `type: "object"` at the top level.
- Define top-level `properties` directly.
- Use `required` for fields the tool must receive.
- Use `additionalProperties: false` when the accepted input set is closed.
- Prefer optional absence over nullable unions for optional fields.
- Keep nested objects shallow and explicit.
- Use simple enums for mode or operation selection.
- Keep op-specific validation in server code when the allowed fields differ by
  operation.
- Represent nullable structured fields as explicit object schemas with
  `"null"` in `type`, not as `anyOf` wrappers around `$ref`.
- Represent variant records with explicit discriminator fields and deterministic
  validation code, not schema composition.

Avoid these schema composition forms in MCP/Claude tool schemas and
MCP-projectable repository schemas:

```json
{ "oneOf": [] }
{ "anyOf": [] }
{ "allOf": [] }
{ "$ref": "#/$defs/input" }
{ "not": {} }
```

Avoid using schema composition to pair an operation with operation-specific
arguments. This is fragile across hosts. Prefer one stable object schema plus
server-side validation.

## Operation Dispatch Pattern

For multi-operation tools, use an explicit operation field and bounded common
arguments:

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["read", "preview", "apply"]
    },
    "spreadsheet_id": {
      "type": "string"
    },
    "range_a1": {
      "type": "string"
    },
    "values": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {}
      }
    }
  },
  "required": ["operation"],
  "additionalProperties": false
}
```

Then validate the operation-to-argument contract inside the server:

- `read` requires `spreadsheet_id` and `range_a1`.
- `preview` requires a target identity and planned changes.
- `apply` requires an approved plan id or bounded write payload.
- The server owns ids, paths, timestamps, digests, and serialization.
- The server returns structured validation failures for missing, incompatible,
  or unauthorized arguments.

## MCPB Manifest Guidance

MCPB manifests describe a packaged extension. Keep package metadata separate
from tool runtime contracts.

Recommended rules:

- Use a lowercase kebab-case package or extension name.
- Keep user-facing names in `display_name` or equivalent manifest metadata.
- Keep `user_config` keys lowercase `snake_case`.
- Avoid dots in `user_config` keys because config interpolation often uses
  dotted lookup notation such as `${user_config.key}`.
- Do not embed tokens, OAuth secrets, service-account keys, cookies, bearer
  headers, or raw credential material in the package.
- Pass credentials through approved host configuration, environment variables,
  or runtime-specific secure storage.
- Validate the manifest, then separately smoke-test the installed package in
  each target host.

## Server Validation Responsibilities

The LLM submits bounded semantic intent. The MCP server creates the canonical
runtime action.

The server should own:

- tool dispatch
- argument validation
- artifact ids and paths
- schema version stamping
- timestamps
- digest calculation
- serialization
- permission checks
- dry-run and apply gates
- audit log naming
- host-specific recovery messages

When exactness matters, expose a deterministic submit/apply tool instead of
asking the LLM to emit final machine-consumed JSON in chat.

## Review Checklist

Before shipping an MCP/MCPB surface:

- Tool names match `^[a-zA-Z0-9_-]{1,64}$`.
- Tool names use canonical `namespace_verb` form.
- No tool name contains a dot.
- No config key or input property depends on dotted lookup semantics.
- Every tool `input_schema` has top-level `type: "object"`.
- No tool `input_schema` uses top-level `oneOf`, `anyOf`, `allOf`, `not`, or
  `$ref`-only schemas.
- Multi-operation tools use `operation` enum plus server-side validation.
- MCP-projectable repository schemas avoid `oneOf`, `anyOf`, and `allOf`.
- Tool inputs are either direct object schemas or compatibility wrappers over
  internal artifact schemas.
- MCPB manifest validation passes.
- Claude-targeted smoke test passes in the actual target host.
- Error responses are structured and actionable.

## Agent Instruction Snippet

Use this wording in global `AGENTS.md` or `CLAUDE.md` files that guide
MCP/MCPB work:

```markdown
## MCP And MCPB Authoring

Before designing or changing MCP servers, MCP tool definitions, MCPB manifests,
Claude-compatible tool surfaces, or repository JSON schemas intended to be
projected into those surfaces, consult the MCP/MCPB authoring guide.

- Use canonical tool names in `namespace_verb` form matching
  `^[a-zA-Z0-9_-]{1,64}$`.
- Use underscore-separated names for tool names, user config keys, and tool
  input property names.
- Keep MCP tool `input_schema` values as direct top-level object schemas.
- Express multi-operation tools with an `operation` enum and server-side
  validation instead of top-level `oneOf`, `anyOf`, or `allOf`.
- Keep MCP-projectable repository schemas free of `oneOf`, `anyOf`, and
  `allOf`; use explicit fields plus deterministic validation code for variant
  behavior.
```

## Source References

- MCP tool specification: https://modelcontextprotocol.io/specification/draft/server/tools
- MCPB packaging project: https://github.com/modelcontextprotocol/mcpb
- Claude tool definition rules: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
