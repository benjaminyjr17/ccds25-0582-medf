# System Architecture Diagram

- The Streamlit UI orchestrates user interactions and sends HTTP/JSON requests to FastAPI endpoints.
- FastAPI routes evaluation, conflict detection, and Pareto analysis into dedicated core engines.
- Framework priors are derived from YAML-based framework structure and combined with stakeholder preferences via product pooling.
- Stakeholder profiles are read from SQLite, while run and audit logs can be persisted for traceability.
- Outputs are rendered as charts and downloadable JSON artifacts for report-ready analysis.

```mermaid
flowchart LR

subgraph Frontend[Frontend]
  U[User / Examiner]
  UI[Streamlit App\nPages: Evaluate, Conflicts, Pareto, Case Studies, About Methodology]
  U --> UI
end

subgraph API[API Layer]
  H[GET /api/health]
  F[GET /api/frameworks]
  S[GET /api/stakeholders]
  E[POST /api/evaluate]
  C[POST /api/conflicts]
  P[POST /api/pareto]
end

subgraph Engines[Core Engines]
  REG[Framework Registry Loader]
  PR[Framework Prior Derivation\n(section/coverage-based)]
  SW[Stakeholder Weights\n(DB defaults + overrides)]
  EW[Effective Weights\n(product pooling + renormalization)]
  SC[Scoring Engine\n(TOPSIS + WSM)]
  CO[Conflict Engine\n(weights-only + contribution-based + Spearman)]
  PA[Pareto Engine\n(dominance checks/frontier)]
end

subgraph Data[Data / Config]
  YAML[Framework YAMLs\neu_altai.yaml, nist_ai_rmf.yaml, sg_mgaf.yaml]
  DB[SQLite\nstakeholders, profiles]
  LOG[Audit / Run Logs]
end

subgraph Outputs[Outputs]
  RAD[Radar Charts]
  HEAT[Conflict Heatmaps]
  PAR[Pareto Scatter / Tables]
  JSON[JSON Results / Downloads]
end

subgraph QA[Quality / Validation]
  T[Pytest Suite\n(unit + E2E)]
end

NOTE[Legend: Unified 6D ontology used across frameworks.]

UI -->|HTTP/JSON| H
UI -->|HTTP/JSON| F
UI -->|HTTP/JSON| S
UI -->|HTTP/JSON| E
UI -->|HTTP/JSON| C
UI -->|HTTP/JSON| P

YAML --> REG
REG --> PR
DB --> SW
SW --> EW
PR --> EW
EW --> SC

E --> EW
E --> SC
C --> CO
P --> PA

SC --> JSON
SC --> RAD
CO --> JSON
CO --> HEAT
PA --> JSON
PA --> PAR

LOG -. optional write .-> E
LOG -. optional write .-> C
LOG -. optional write .-> P

T -. TestClient/API checks .-> API
NOTE --- Engines
```

## Render Instructions

- Option 1: Copy the Mermaid block into the Mermaid Live Editor and export SVG or PNG.
- Option 2: If Mermaid CLI (`mmdc`) is installed, run the helper script:
  - `sh tools/render_architecture_diagram.sh`

The source of truth is `docs/system_architecture.mmd`; regenerate exported images whenever the architecture changes.
