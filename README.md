# MEDF — Multi-stakeholder Ethical Decision Framework for AI Systems  
**NTU CCDS Final Year Project (CCDS25-0582)**  
Author: Benjamin Oliver Yick  
Supervisor: Dr Zhang Jiehuang  

---

## Research Problem

AI governance tools evaluate ethical compliance through a single framework and a single evaluator perspective.  
They do not:

- Compare AI systems across multiple ethical frameworks simultaneously  
- Model disagreement between stakeholder groups  
- Quantify stakeholder-weighted ethical trade-offs  

This project addresses that gap.

---

## Research Contribution

This work delivers a computational framework that:

1. Harmonises three major AI governance frameworks:
   - EU Assessment List for Trustworthy AI (ALTAI)
   - NIST AI Risk Management Framework (AI RMF)
   - Singapore Model AI Governance Framework (MGAF)

2. Applies Multi-Criteria Decision Analysis (MCDA):
   - AHP (weight derivation)
   - TOPSIS (primary scoring)
   - WSM (baseline comparator)

3. Detects stakeholder disagreement using:
   - Spearman rank correlation (ρ)
   - Conflict classification (Low / Moderate / High)

4. Computes Pareto-optimal compromise configurations via:
   - NSGA-II (pymoo implementation)

5. Produces reproducible, auditable intermediate computations for academic verification.

No existing open-source tool currently integrates all five capabilities.

---

## Methodological Foundation

This project follows Design Science Research (Peffers et al., 2007):

1. Problem Identification  
2. Objective Definition  
3. Design & Development  
4. Demonstration (3 case studies)  
5. Evaluation (expert validation + usability + ablation study)  
6. Communication  

Validation includes:

- Content Validity Index (I-CVI, S-CVI/Ave)  
- Krippendorff’s Alpha (bootstrapped CI)  
- System Usability Scale (SUS)  
- Wilcoxon signed-rank test  
- Friedman test  
- Cliff’s Delta effect size  

---

## System Architecture

### Backend
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- SQLite

### Scoring & Analysis
- pyDecision (TOPSIS, AHP, WSM)
- NumPy (reference verification)
- SciPy (Spearman correlation)
- pymoo (NSGA-II)

### Frontend
- Streamlit
- Plotly interactive visualisation

### Configuration
- Framework definitions stored as YAML
- Version-controlled harmonisation mapping

---

## Core Capabilities

### Cross-Framework Evaluation
Evaluate a single AI system against EU ALTAI, NIST AI RMF, and Singapore MGAF simultaneously.

### Stakeholder-Weighted Scoring
Apply distinct weight vectors for:
- Developer
- Regulator
- Affected Community
- Custom stakeholder

### Conflict Detection
Quantify disagreement between stakeholder ethical rankings using Spearman ρ.

### Pareto Frontier Analysis
Generate non-dominated compromise weight configurations.

### Interactive Dashboard
- Radar charts
- Correlation heatmaps
- Pareto scatter plots
- Real-time weight adjustment

---

## Project Structure

```text
ccds25-0582-medf/
│
├── app/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── scoring_engine.py
│   ├── conflict_detection.py
│   ├── framework_registry.py
│   ├── routers/
│   │   ├── evaluate.py
│   │   ├── conflicts.py
│   │   ├── frameworks.py
│   │   └── stakeholders.py
│   └── frameworks/
│       ├── eu_altai.yaml
│       ├── nist_ai_rmf.yaml
│       └── sg_mgaf.yaml
│
├── dashboard/
│   └── app.py
│
├── case_studies/
│   ├── facial_recognition.json
│   ├── hiring_algorithm.json
│   └── healthcare_diagnostic.json
│
├── tests/
│   ├── test_models.py
│   ├── test_scoring_engine.py
│   ├── test_conflict_detection.py
│   └── test_api_endpoints.py
│
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Quick Start

### Step 1: Create Vitual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run Backend API

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger:
```
http://localhost:8000/api/docs
```

### Step 4: Run Streamlit Dashboard

```bash
streamlit run dashboard/app.py
```

---

## Reproducibility

- Hand-verified TOPSIS computation included
- Unit tests cover scoring, AHP consistency, conflict detection
- Statistical analysis script provided
- Docker support available
- YAML framework definitions version-controlled

---

## Case Studies

1. Facial Recognition for Law Enforcement  
2. Hiring Recommendation Algorithm  
3. Healthcare Diagnostic AI  

Each case study demonstrates different stakeholder conflict structures.

---

## Limitations

- Limited to 3 frameworks (extensible via YAML)
- Small expert sample (acknowledged in validation)
- Single-machine prototype (not horizontally scalable)
- Harmonisation mapping requires expert validation

These limitations do not undermine the core contribution: demonstrating the feasibility of multi-stakeholder cross-framework ethical AI assessment.

---

## Repository Description (Short Version)

Cross-framework ethical AI assessment platform with stakeholder-weighted MCDA scoring, conflict detection (Spearman ρ), and Pareto trade-off analysis (NSGA-II). NTU CCDS FYP CCDS25-0582.