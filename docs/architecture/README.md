# System Architecture Diagram

This folder contains the report-ready system architecture diagram source and exports.

## Files

- `system_architecture.mmd`: Mermaid source file (single-page architecture diagram)
- `system_architecture.svg`: Committed vector export for Overleaf/Word inclusion
- `system_architecture.png`: Optional raster export (not required to commit)

## Regenerate SVG

```bash
npx -p @mermaid-js/mermaid-cli mmdc -i docs/architecture/system_architecture.mmd -o docs/architecture/system_architecture.svg
```

## Optional PNG export

```bash
npx -p @mermaid-js/mermaid-cli mmdc -i docs/architecture/system_architecture.mmd -o docs/architecture/system_architecture.png
```

## Notes

- If the backend architecture changes, update `system_architecture.mmd` first, then regenerate exports.
- Keep the SVG committed so the figure can be directly embedded in report tooling.
