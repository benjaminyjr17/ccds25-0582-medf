#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INPUT="$REPO_ROOT/docs/system_architecture.mmd"
OUTPUT_SVG="$REPO_ROOT/docs/system_architecture.svg"
OUTPUT_PNG="$REPO_ROOT/docs/system_architecture.png"

if [ ! -f "$INPUT" ]; then
  echo "Missing input file: $INPUT" >&2
  exit 1
fi

if command -v mmdc >/dev/null 2>&1; then
  echo "Rendering architecture diagram with mmdc..."
  mmdc -i "$INPUT" -o "$OUTPUT_SVG"
  mmdc -i "$INPUT" -o "$OUTPUT_PNG"
  echo "Generated: $OUTPUT_SVG"
  echo "Generated: $OUTPUT_PNG"
  exit 0
fi

echo "Mermaid CLI (mmdc) not found."
echo "Install it with: npm install -g @mermaid-js/mermaid-cli"
echo "Then run: mmdc -i docs/system_architecture.mmd -o docs/system_architecture.svg"
