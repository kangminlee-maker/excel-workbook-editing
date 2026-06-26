# Excel Projects

Excel project folders should represent workbook families, not only file paths.

Recommended folder shape:

```text
projects/excel/<workbook-family-id>/
  project.json
  instances/
    <exact-revision-id>/
      identity.json
      source-observation.json
```

## Identity Layers

| Identity | Source | Use |
| --- | --- | --- |
| `exact_revision_id` | SHA-256 of the exact file bytes. | Detect the exact same copy. |
| `workbook_family_id` | Normalized workbook manifest and formula-structure fingerprint. | Group renamed or copied workbooks that appear to share the same design. |
| `local_boundary_id` | User-confirmed organization/project/team/workbook-family boundary. | Prevent false merges across different contexts. |

## Review-Required Cases

Create or attach to an Excel workbook-family project only after review when:

- file names match but fingerprints differ materially;
- fingerprints are similar but sheet structure or formula signatures drift;
- local boundary is different or unknown;
- the workbook has been manually edited after copying;
- generator metadata or custom properties conflict with structural evidence.
