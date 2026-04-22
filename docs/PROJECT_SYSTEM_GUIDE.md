# AI Course Project Evaluator

## Detailed System Guide

This document describes the current finalized implementation of the project as it exists in the codebase right now.

Last updated for the current finalized code state in this repository.

It is intentionally detailed and is meant to answer:

- what the system does
- how it is structured
- which tech stack is used and why
- where data is stored
- how evaluation and marks computation work
- how continuous stage-based submission works
- how final marks are computed and compared
- which parts are primary, which parts are compatibility layers, and which constraints are still present

---

## 0. Reading Guide

This document is intentionally long, because it is meant to work as a handoff and reference file rather than a short README.

If you want to understand the project quickly, read in this order:

1. Section 1 for the product summary.
2. Sections 4 to 11 for repository structure, configuration, schema, startup, and routes.
3. Sections 12 to 20 for evaluation logic, RAG flow, stage logic, score scaling, and finalization math.
4. Sections 21 to 29 for what the student and teacher actually see.
5. Sections 30 to 35 for internal payload formats, design thinking, constraints, and the short mental model.

If you are coming back later and only need specific answers:

- "How are final marks computed?" -> Section 19
- "How are rank and comparison computed?" -> Section 20
- "Where is data stored?" -> Sections 6 to 8 and Section 30
- "How does stage chronology work?" -> Section 13
- "How are earlier recommendations carried forward?" -> Section 24
- "Why do legacy tables still exist?" -> Section 27

Current finalized product decisions:

- the student-facing workflow is stage-first
- only one active submission is allowed per stage per project
- stages must be uploaded in chronological order
- stage deletions must follow reverse chronology
- final marks are the sum of scaled stage marks, not the latest stage score
- class comparison is mathematical
- letter grades are removed from the UI
- rank and z-score are still stored
- legacy single-submission support still exists for compatibility and PDF reporting

---

## 1. Product Summary

The application is a web-based AI project evaluator for course projects.

It supports two broad workflows:

1. Legacy single-submission workflow
   - student uploads one full project document
   - backend extracts content, chunks it, embeds it, stores vectors, retrieves evidence, and evaluates it

2. Continuous stage-based workflow
   - student progresses through multiple stages
   - each stage is evaluated separately
   - previous stages are used as reference context
   - later stages check whether previous recommendations were actually implemented
   - final marks are built from the sum of stage marks

The current UI is stage-first.

That means:

- students primarily interact with stage submissions
- teacher dashboards primarily emphasize stage progress and summed marks
- the old single-upload pipeline still exists in the backend and is still useful for compatibility and report generation

---

## 2. Tech Stack Used

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic

Why:

- FastAPI provides a clean API layer with request validation, simple dependency injection, and structured route organization.
- SQLAlchemy is used for relational modeling and database interaction.
- Pydantic is used for request and response schemas where needed.

### Frontend

- React
- React Router
- Tailwind CSS
- Recharts
- Axios

Why:

- React is used for a component-based dashboard UI.
- React Router powers student, teacher, and stage-feedback pages.
- Tailwind provides fast UI composition and consistent styling.
- Recharts is used for class comparison and score visualizations.
- Axios handles API communication.

### Database

- PostgreSQL

Why:

- PostgreSQL is the source of truth for structured data:
  - users
  - submissions
  - evaluations
  - stage definitions
  - project tracks
  - marks/rank records

### Vector Store

- FAISS

Why:

- FAISS provides local vector indexing and similarity search for retrieval.
- It is used per legacy submission, stored on disk rather than in PostgreSQL.

### LLM Provider Layer

- OpenAI-compatible Python client
- Configured by default to Gemini via:
  - `LLM_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/`
  - `LLM_CHAT_MODEL=gemini-2.5-flash`
  - `LLM_EMBEDDING_MODEL=gemini-embedding-001`

Why:

- The code uses the OpenAI client abstraction because Gemini exposes an OpenAI-compatible endpoint.
- This keeps the provider layer simple while still allowing model/provider changes through `.env`.

---

## 3. High-Level Runtime Architecture

```text
React frontend
    ->
FastAPI routes
    ->
Service layer
    ->
PostgreSQL + local file storage + FAISS + Gemini/OpenAI-compatible API
```

At a higher level:

```text
Student/Teacher UI
    ->
API request
    ->
Validation and DB lookup
    ->
File/text ingestion
    ->
Chunking / embedding / retrieval
    ->
Prompted evaluation
    ->
Structured JSON output
    ->
Stored evaluation + marks + dashboard payload
```

### Three primary runtime flows

The easiest way to reason about the live system is to think in terms of three main flows.

#### Flow A: Login and dashboard hydration

```text
User signs in
    ->
/auth/login
    ->
student or teacher record resolved
    ->
frontend stores session state
    ->
role-specific dashboard API is loaded
```

#### Flow B: Continuous stage submission and evaluation

```text
Student chooses existing project or new project
    ->
/continuous/upload
    ->
chronology and duplicate-stage validation
    ->
file or text ingestion
    ->
stage submission stored in PostgreSQL
    ->
stage evaluation runs
    ->
dashboard shows updated marks and feedback
```

#### Flow C: Teacher finalization and cohort comparison

```text
Teacher clicks finalize
    ->
/finalize
    ->
latest stage marks gathered per student
    ->
missing evaluations filled if needed
    ->
final cumulative marks computed
    ->
mean, standard deviation, z-score, and rank computed
    ->
comparison data stored and dashboards refreshed
```

---

## 4. Repository Structure

Current top-level structure:

```text
backend/
frontend/
.env
.env.example
docker-compose.yml
README.md
docs/
```

### Backend structure

```text
backend/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  rag_pipeline.py
  routes/
    auth.py
    continuous.py
    students.py
    submissions.py
    teacher.py
  services/
    auth.py
    continuous_evaluation.py
    grading.py
    ingestion.py
    llm_client.py
    master_brief.py
    reporting.py
    seed.py
    serializers.py
    student_admin.py
    vector_store.py
  prompts/
    evaluation_prompts.py
    sample_prompts.md
  data/
    uploads/
    faiss/
    reports/
  .vendor/
```

### Frontend structure

```text
frontend/
  src/
    App.jsx
    main.jsx
    api/
      client.js
    components/
      ...
    context/
      AuthContext.jsx
    pages/
      LoginPage.jsx
      StudentDashboard.jsx
      TeacherDashboard.jsx
      StageFeedbackPage.jsx
    utils/
      errors.js
```

---

## 5. Configuration Layer

Main config file:

- `backend/config.py`

Important settings:

- `database_url`
- `cors_origins`
- `upload_dir`
- `faiss_dir`
- `reports_dir`
- `llm_api_key`
- `llm_api_base`
- `llm_chat_model`
- `llm_embedding_model`
- `chunk_word_size`
- `chunk_word_overlap`
- `retrieval_top_k`
- `plagiarism_threshold`

Current default model config is Gemini-compatible.

### Important current defaults

- chunk size: `700` words
- chunk overlap: `120` words
- retrieval top-k: `5`
- plagiarism threshold: `0.92`

### Why directories are explicitly configured

The backend stores three different data types outside PostgreSQL:

1. uploaded source files
2. FAISS indices and metadata
3. generated PDF reports

The config object ensures those folders exist at startup.

---

## 6. Database Layer

Database setup:

- `backend/database.py`

The application uses:

- a global SQLAlchemy engine
- `SessionLocal`
- declarative `Base`
- `init_db()` calling `Base.metadata.create_all()`

This means the schema is created automatically when the backend starts.

There is no Alembic migration system in the current implementation.

---

## 7. Data Model

Main models are defined in:

- `backend/models.py`

### 7.1 Student

Purpose:

- stores student identity
- owns legacy submissions
- owns continuous project tracks
- has one marks/rank record in the `grades` table

Important fields:

- `id`
- `name`
- `email`
- `created_at`

### 7.2 Teacher

Purpose:

- stores teacher/admin login identity

Important fields:

- `id`
- `name`
- `email`
- `password`

### 7.3 Submission

Purpose:

- legacy single-project submission

Important fields:

- `student_id`
- `title`
- `original_filename`
- `file_type`
- `storage_path`
- `content`
- `created_at`

### 7.4 Evaluation

Purpose:

- evaluation result for a legacy submission

Important fields:

- criterion scores:
  - `innovation_score`
  - `technical_score`
  - `clarity_score`
  - `impact_score`
- `total_score`
- `feedback` as JSON
- `features` as JSON
- `retrieved_chunks` as JSON
- `weak_sections` as JSON
- `plagiarism_matches` as JSON
- `draft` flag

### 7.5 ProjectTrack

Purpose:

- represents one continuous project owned by one student

Important fields:

- `student_id`
- `title`
- `created_at`

### 7.6 StageDefinition

Purpose:

- teacher-configurable stage structure

Important fields:

- `name`
- `stage_order`
- `max_marks`

Current seeded defaults:

- Stage 1
- Stage 2
- Stage 3

Each initially has `10.0` max marks.

### 7.7 StageSubmission

Purpose:

- one stage checkpoint for one project

Important fields:

- `project_id`
- `stage_id`
- `original_filename`
- `file_type`
- `storage_path`
- `content`
- `created_at`

### 7.8 StageEvaluation

Purpose:

- evaluation for one stage submission

Important fields:

- `raw_total_score`
- `scaled_score`
- `max_marks`
- `feedback` as JSON
- `features` as JSON
- `context_snapshot` as JSON
- `retrieved_chunks` as JSON
- `weak_sections` as JSON

### 7.9 Grade

Purpose:

- stores finalized marks-comparison data

Important fields:

- `final_score`
- `grade`
- `z_score`
- `rank`

Important implementation note:

- the UI no longer shows letter grades
- however, this table is still used to persist:
  - final summed marks
  - rank
  - z-score
- the `grade` string field still exists for schema compatibility and is currently written as `"NA"`

### 7.10 LegacySubmissionStageLink

Purpose:

- links old legacy submissions to migrated Stage 1 records

Why it exists:

- old single-upload submissions are migrated into Stage 1 on backend startup
- this preserves continuity while the system shifted to stage-first behavior

### 7.11 MasterBrief

Purpose:

- stores the teacher-uploaded topic approval brief

Important fields:

- `title`
- `content`
- `original_filename`
- `file_type`
- `storage_path`
- `created_at`
- `updated_at`

---

## 8. Where Data Is Stored

### 8.1 PostgreSQL

Stored in PostgreSQL:

- students
- teachers
- legacy submissions
- legacy evaluations
- continuous project tracks
- stage definitions
- stage submissions
- stage evaluations
- final marks/rank records
- master brief
- migration links

### 8.2 File system storage

Stored on disk:

#### Uploaded files

Directory:

- `backend/data/uploads/`

Format:

- original uploaded file bytes
- stored with a generated UUID-prefixed sanitized filename

#### FAISS vector data

Directory pattern:

- `backend/data/faiss/<submission_id>/`

Files inside:

- `index.faiss`
- `metadata.json`

`metadata.json` stores:

- `submission_id`
- `chunks`
- `centroid`
- `dimension`

#### Generated reports

Directory:

- `backend/data/reports/`

File pattern:

- `submission_<id>_report.pdf`

### 8.3 Local browser storage

Stored in browser `localStorage`:

- currently signed-in user object

Key used:

- `ai-course-project-evaluator-user`

---

## 9. Authentication Model

Backend auth logic:

- `backend/services/auth.py`

Frontend auth state:

- `frontend/src/context/AuthContext.jsx`

### Student auth behavior

Students do not use passwords in the current implementation.

Behavior:

- if a student logs in with a new email, a new `Student` row is created automatically
- if the email already exists, that student is reused
- if a name is supplied and it differs, the name is updated

This means student identity is email-based and lightweight.

### Teacher auth behavior

Teachers use email + password.

Seeded demo teacher:

- email: `teacher@example.com`
- password: `teach123`

---

## 10. Startup Behavior

Main entrypoint:

- `backend/main.py`

Startup flow:

1. ensure directories exist
2. initialize database tables
3. seed demo data
4. migrate old legacy submissions into Stage 1

### Demo seed behavior

Seed logic:

- `backend/services/seed.py`

What gets seeded:

- one teacher
- default stage definitions
- demo students, but only if the student table is empty

Important behavior:

- if students already exist, demo students are not recreated

---

## 11. API Surface

### Auth

- `POST /auth/login`

### Legacy submission flow

- `POST /upload`
- `POST /evaluate`

### Student dashboard

- `GET /student/{id}`

### Teacher dashboard

- `GET /teacher/dashboard`
- `POST /finalize`
- `GET /teacher/report/{submission_id}`
- `DELETE /teacher/student/{student_id}`
- `POST /teacher/master-brief`
- `PUT /teacher/stages/{stage_id}`

### Continuous stage flow

- `POST /continuous/upload`
- `POST /continuous/evaluate`
- `GET /continuous/stage-submission/{stage_submission_id}`
- `DELETE /continuous/stage-submission/{stage_submission_id}?student_id=...`

---

## 12. Legacy RAG Evaluation Flow

Main implementation:

- `backend/rag_pipeline.py`

### Step-by-step

1. Student uploads PDF or text
2. Backend extracts text with `PyMuPDF` for PDF, or direct UTF-8 decode for text files
3. Text is cleaned
4. Text is chunked into overlapping word chunks
5. Chunk embeddings are created
6. Chunks and embeddings are saved into a FAISS index
7. During evaluation, one query embedding is created from a fixed evaluation query
8. Top-k similar chunks are retrieved
9. Three separate LLM JSON calls are made:
   - feature extraction
   - scoring
   - feedback
10. Weighted total is computed in Python
11. Weak sections and plagiarism matches are attached
12. Evaluation row is persisted in PostgreSQL

### Why this is multi-step instead of one prompt

The system intentionally separates:

- feature extraction
- numeric scoring
- narrative feedback

This reduces single-prompt brittleness and makes the output structure cleaner.

---

## 13. Continuous Stage Evaluation Flow

Main implementation:

- `backend/services/continuous_evaluation.py`

### Stage upload flow

1. Student selects an existing project or creates a new one
2. Backend validates stage rules:
   - project must start at Stage 1
   - only one submission per stage is allowed
   - stage order must be chronological
3. Stage content is saved
4. Stage evaluation runs automatically if provider config is valid

### Current stage rules

The following rules are now enforced:

1. One submission per stage per project
   - duplicate stage submissions are rejected

2. Chronology only
   - Stage 2 cannot be submitted before Stage 1
   - Stage 3 cannot be submitted before Stage 2

3. Reverse chronology for deletion
   - a student cannot delete Stage 1 while Stage 2 exists
   - later stages must be deleted first

### Stage evaluation flow

1. Retrieve current stage submission
2. Validate master-brief topic alignment
3. Build current-stage chunk set
4. Build prior-stage context
5. Run feature extraction prompt with prior-stage context
6. Run scoring prompt with prior-stage context
7. Run feedback prompt with prior-stage context
8. Run a separate carry-forward verification step that checks whether prior recommendations were implemented
9. Store:
   - stage marks
   - feedback
   - carry-forward results
   - weak sections
   - retrieved evidence
   - context snapshot

The stored stage evaluation is intentionally richer than just a score.

It also preserves the evaluation context used at that moment:

- project title
- stage name and stage order
- stage max marks
- prior-stage reference summaries
- prior-stage recommendations
- current retrieved evidence

This is what lets later stages be continuity-aware instead of being treated as isolated standalone files.

---

## 14. Anti-Hallucination Strategy

Main prompt guardrails are in:

- `backend/prompts/evaluation_prompts.py`

Key guardrails:

- ONLY use provided project content
- if info is missing, return `"Insufficient data"`
- never fabricate technologies, metrics, outcomes, or implementation details
- use retrieved chunks only
- return JSON only

These rules are applied to:

- feature extraction
- scoring
- feedback
- master brief validation
- carry-forward recommendation verification

---

## 15. Prompting Strategy

Main prompts:

- `FEATURE_EXTRACTION_SYSTEM_PROMPT`
- `SCORING_SYSTEM_PROMPT`
- `FEEDBACK_SYSTEM_PROMPT`

### Feature extraction prompt

Extracts:

- innovation summary
- technologies used
- complexity summary and level
- evidence chunk ids

### Scoring prompt

Returns:

- innovation score
- technical score
- clarity score
- impact score
- criterion justifications
- criterion evidence references

### Feedback prompt

Returns:

- strengths
- weaknesses
- suggestions
- future scope
- weak sections

### Continuous-specific prompt wrapping

For stage evaluation, the base prompt is wrapped with:

- project title
- student name
- current stage
- stage order
- stage max marks
- serialized previous-stage context

This is how later stages become continuity-aware.

---

## 16. Master Brief Topic Gate

Main implementation:

- `backend/services/master_brief.py`

Purpose:

- teacher uploads an approved topic brief
- submissions are validated against that brief before scoring

### If no master brief exists

- evaluation proceeds normally

### If a master brief exists and submission is off-topic

Legacy submission:

- total score is forced to `2.0 / 10`

Stage submission:

- stage score is capped at `min(2.0, stage.max_marks)`

This is intentionally harsher than normal scoring to reject irrelevant work.

---

## 17. Retrieval and Vector Search

Main implementation:

- `backend/services/vector_store.py`

### Storage design

Legacy submissions get their own FAISS directory:

```text
backend/data/faiss/<submission_id>/
  index.faiss
  metadata.json
```

`index.faiss` is a binary vector index file.

`metadata.json` is a human-readable JSON companion file that stores the chunk payloads and centroid data used by retrieval and plagiarism comparison.

Typical structure:

```json
{
  "submission_id": 14,
  "chunks": [
    {
      "chunk_id": 0,
      "text": "project text chunk",
      "start_word": 0,
      "end_word": 700
    }
  ],
  "centroid": [0.0123, -0.0456, 0.0789],
  "dimension": 768
}
```

### Retrieval strategy

The system:

1. normalizes chunk vectors with L2 normalization
2. uses `IndexFlatIP`
3. searches by inner product over normalized vectors
4. effectively treats retrieval as cosine-style similarity

### Why FAISS is not used for stage submissions

Current stage evaluation computes chunk embeddings on the fly for the current stage content and scores chunks directly in memory.

So:

- legacy submissions use persisted FAISS retrieval
- stage submissions use in-process chunk ranking for the current stage

This is an implementation split, not a conceptual split.

---

## 18. Plagiarism Similarity

Current implementation exists for legacy submissions only.

How it works:

1. each legacy submission stores a centroid embedding in `metadata.json`
2. during evaluation, other submission centroids are compared
3. cosine-style similarity is computed
4. matches above threshold are returned

Current threshold:

- `0.92`

Result format includes:

- submission id
- student id
- student name
- similarity

---

## 19. Marks and Score Computation

This is one of the most important parts of the system.

### 19.1 Criterion weights

For both legacy and stage evaluation, the same rubric weights are used:

- Innovation: 30%
- Technical Depth: 30%
- Clarity: 20%
- Impact: 20%

### 19.2 Raw criterion scoring

Each criterion is scored on a `1` to `10` scale.

The backend clamps values into this range.

Formula:

```text
total_score =
  innovation_score * 0.30 +
  technical_score * 0.30 +
  clarity_score * 0.20 +
  impact_score * 0.20
```

### 19.3 Legacy submission total

For legacy submissions:

- `total_score` is the final weighted score
- scale is out of `10`

### 19.4 Stage score normalization

For stage submissions there are two score levels:

1. `raw_total_score`
   - weighted rubric score out of `10`

2. `scaled_score`
   - normalized into that stage's teacher-defined max marks

Formula:

```text
scaled_score = (raw_total_score / 10.0) * stage.max_marks
```

Example:

- raw total: `7.5 / 10`
- stage max marks: `15`
- scaled score: `11.25 / 15`

### 19.5 Final marks for continuous projects

Current finalized behavior:

- final marks are the sum of the latest evaluated stage scores across all stages in that project

Formula:

```text
final_marks =
  latest_stage1_scaled_score +
  latest_stage2_scaled_score +
  latest_stage3_scaled_score + ...
```

Important:

- final marks are not the latest stage score
- final marks are not the raw `10-point` score
- final marks are the accumulated scaled stage marks

### 19.6 Marks possible

The denominator for the final continuous workflow is:

```text
sum(all stage max marks)
```

With default stages:

```text
10 + 10 + 10 = 30
```

So by default, continuous final marks are out of `30`.

If the teacher changes stage max marks, the denominator changes accordingly.

### 19.7 Worked normalization example

Assume the teacher configures:

- Stage 1 max marks = `5`
- Stage 2 max marks = `10`
- Stage 3 max marks = `15`

Assume the evaluator returns these raw rubric totals:

- Stage 1 raw total = `8.0 / 10`
- Stage 2 raw total = `7.2 / 10`
- Stage 3 raw total = `9.1 / 10`

Then scaling happens stage by stage:

```text
Stage 1 scaled = (8.0 / 10.0) * 5  = 4.00
Stage 2 scaled = (7.2 / 10.0) * 10 = 7.20
Stage 3 scaled = (9.1 / 10.0) * 15 = 13.65
```

Final marks become:

```text
4.00 + 7.20 + 13.65 = 24.85 / 30.00
```

This is the key point:

- the latest stage score is `13.65 / 15`
- the running final marks are `24.85 / 30`
- the final marks must never be replaced by just the latest stage score

### 19.8 Running marks before all stages exist

If only Stage 1 and Stage 2 are evaluated in the example above, the dashboard still shows a running cumulative total against the full configured denominator:

```text
4.00 + 7.20 = 11.20 / 30.00
```

So the student is not shown "7.20 / 10" as a fake final mark. The system keeps the full stage program in view and only increases earned marks as later stages are completed.

---

## 20. Finalization and Class Comparison

Main implementation:

- `backend/services/grading.py`

### What finalize does

When the teacher clicks finalize:

1. collect all students
2. for each student:
   - if stage-based project exists, use latest stage submission for each stage
   - if any stage lacks evaluation, evaluate it
   - sum scaled stage marks
   - otherwise fall back to legacy final evaluation if needed
3. compute cohort statistics
4. assign rank
5. compute z-score
6. store final score, rank, z-score in the `grades` table

### Current comparison math

Given a pool of final marks:

```text
mean = average(all final marks)
std = population standard deviation
z = (student_marks - mean) / std
```

### Worked ranking example

Assume three students have these finalized cumulative marks:

```text
[24, 18, 12]
```

Then:

```text
mean = 18
population std dev = 4.899
```

Their z-scores are approximately:

```text
24 ->  1.2247
18 ->  0.0000
12 -> -1.2247
```

And the rank order becomes:

```text
Rank 1 -> 24
Rank 2 -> 18
Rank 3 -> 12
```

### Important current behavior

- letter grades are no longer shown in the UI
- the rank list and dashboards use:
  - final marks
  - class average
  - top score
  - rank
  - z-score internally
- dashboards prefer the live summed stage marks for current display
- the `grades` table stores the last finalized comparison snapshot

### Compatibility note

The old `grades.grade` column still exists.

Current code writes:

```text
grade = "NA"
```

This is purely to satisfy the old schema.

---

## 21. Student Dashboard Behavior

Main page:

- `frontend/src/pages/StudentDashboard.jsx`

### What the student sees

- project count
- stage upload count
- latest stage marks
- final summed marks
- class rank
- class average
- latest stage feedback summary
- stage-wise marks breakdown
- stage progress timeline
- link to full feedback page per stage

### Upload behavior

The current upload card:

- lets the student choose:
  - existing project
  - new project
- automatically exposes only the next stage that is valid

This is important because it prevents Stage 2 from being blocked by title mismatch.

The dashboard also relies on serialization that keeps only the latest submission per stage visible.

That means:

- if older duplicate rows exist historically, the student does not get a confusing duplicate stage timeline
- the student sees one effective current state for Stage 1, one for Stage 2, and one for Stage 3

---

## 22. Teacher Dashboard Behavior

Main page:

- `frontend/src/pages/TeacherDashboard.jsx`

### What the teacher sees

- student count
- evaluated count
- mean marks
- top marks
- submission review table
- class marks comparison chart
- master brief uploader
- stage settings editor
- continuous progress review table
- rank list
- stage-wise marks distribution matrix

### What the teacher can do

- refresh evaluation for a submission or stage
- finalize marks ranking
- upload or replace the master brief
- change stage names and max marks
- delete students
- open stage feedback pages
- download legacy PDF reports

---

## 23. Dedicated Stage Feedback Pages

Main page:

- `frontend/src/pages/StageFeedbackPage.jsx`

Routes:

- `/student/stage-feedback/:stageSubmissionId`
- `/teacher/stage-feedback/:stageSubmissionId`

### Why this page exists

The dashboard cards became too compressed for real review.

So each stage now has a dedicated page that shows:

- stage marks
- final accumulated marks
- class rank if finalized
- submission content
- strengths
- weaknesses
- recommended next actions
- future scope
- recommendation follow-through
- weak sections
- retrieved evidence chunks
- stage-wise marks breakdown

This is now the cleanest place to inspect a stage evaluation.

---

## 24. Recommendation Carry-Forward Logic

This is the continuity logic between stages.

Main implementation:

- `backend/services/continuous_evaluation.py`

### How it works

When evaluating Stage N:

1. collect prior stages
2. extract their suggestions
3. compare those suggestions against current stage retrieved chunks
4. generate:
   - summary
   - addressed items
   - pending items

This output is stored in:

- `feedback["carry_forward"]`
- `context_snapshot["progress_on_previous_feedback"]`

### Important scoring intent

The prompt now explicitly tells the model:

- if earlier recommendations are still missing, reflect that gap in current-stage marks and feedback

So carry-forward is not just informational.
It is intended to influence the later stage evaluation quality and marks.

---

## 25. Stage-Wise Marks Visibility

This is now visible to both student and teacher.

### Student side

Component:

- `frontend/src/components/StageMarksBreakdown.jsx`

Shows:

- each configured stage
- its scaled marks
- its max marks
- raw rubric score if available
- total final marks
- direct link to that stage's feedback page

### Teacher side

Component:

- `frontend/src/components/StageMarksMatrix.jsx`

Shows:

- one row per student
- one column per stage
- per-stage marks
- total marks
- rank
- links into stage feedback pages

---

## 26. Serialization Strategy

Main implementation:

- `backend/services/serializers.py`

Important behavior:

- project serialization returns only the latest submission per stage

Why:

- older data may still exist historically
- current UI should show one current stage state, not duplicate rows

So the serializer acts as a stability layer between raw DB history and dashboard presentation.

---

## 27. Legacy Compatibility Layer

The app still contains legacy single-submission support.

Examples:

- `POST /upload`
- `POST /evaluate`
- `Evaluation` table
- `Submission` table
- `teacher/report/{submission_id}`

### Why it still exists

- earlier versions of the app used this mode
- it still supports report generation
- old records are preserved instead of being discarded

### Migration behavior

At startup, legacy submissions are migrated into Stage 1 through:

- `LegacySubmissionStageLink`

This lets the stage-first system continue from old data.

---

## 28. Reporting

Main implementation:

- `backend/services/reporting.py`

Current PDF report contents:

- student details
- legacy evaluation type
- criterion scores
- weighted total
- final marks and rank if available
- strengths
- weaknesses
- suggestions
- future scope
- weak sections
- plagiarism matches

Important current limitation:

- PDF reporting is built around legacy submission records
- stage-first projects may not always map perfectly to the old report workflow

---

## 29. Frontend Routing

Frontend routes:

- `/login`
- `/student`
- `/teacher`
- `/student/stage-feedback/:stageSubmissionId`
- `/teacher/stage-feedback/:stageSubmissionId`

Router file:

- `frontend/src/App.jsx`

Protected route behavior:

- student routes require role `student`
- teacher routes require role `teacher`

---

## 30. Data Formats Used Internally

### 30.1 Chunk format

```json
{
  "chunk_id": 0,
  "text": "chunk text",
  "start_word": 0,
  "end_word": 700,
  "score": 0.91
}
```

### 30.2 Legacy feedback format

```json
{
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "future_scope": ["..."],
  "criterion_justifications": {
    "innovation": "...",
    "technical_depth": "...",
    "clarity": "...",
    "impact": "..."
  },
  "evidence": {
    "innovation": [0],
    "technical_depth": [1],
    "clarity": [2],
    "impact": [3]
  }
}
```

### 30.3 Stage feedback format

```json
{
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["..."],
  "future_scope": ["..."],
  "carry_forward": {
    "summary": "...",
    "addressed_items": ["..."],
    "pending_items": ["..."]
  }
}
```

### 30.4 Stage breakdown format

```json
{
  "stage_id": 1,
  "stage_name": "Stage 1",
  "stage_order": 1,
  "max_marks": 10.0,
  "scaled_score": 8.4,
  "raw_total_score": 8.4,
  "submission_id": 12
}
```

### 30.5 Final marks payload format

```json
{
  "earned": 24.7,
  "possible": 30.0,
  "rank": 2,
  "z_score": 0.8431,
  "finalized_at": "..."
}
```

---

## 31. Current Design Thinking Applied

This section explains the main engineering decisions behind the current implementation.

### Split structured storage from vector storage

Reason:

- relational data and retrieval data have different access patterns
- PostgreSQL remains the source of truth
- FAISS is used only where vector similarity is needed

### Use explicit JSON outputs from the model

Reason:

- easier parsing
- fewer brittle regex hacks
- easier UI consumption
- more stable evaluation pipeline

### Prefer stage continuity over isolated stage scoring

Reason:

- course projects usually evolve
- Stage 2 should not be judged blindly without Stage 1 context
- recommendations should matter later

### Keep compatibility instead of breaking old data

Reason:

- earlier legacy submissions already existed
- migration to Stage 1 preserved continuity

### Remove grades from the UI but keep rank storage

Reason:

- product direction shifted from letter grades to marks + comparison
- rank and z-score are still useful for teacher comparison
- schema still contains old grade fields, so the app uses them as compatibility storage

---

## 32. Known Current Constraints

These are not necessarily bugs. They are important realities of the current implementation.

1. The `grades` table still exists even though grade letters are no longer shown.

2. The backend still contains legacy single-submission flows.

3. FAISS indexing is persistent for legacy submissions, but stage retrieval is currently in-memory per stage evaluation.

4. PDF reporting is still more aligned to legacy submissions than fully stage-native reporting.

5. Database schema is created directly with SQLAlchemy `create_all()`; there is no migration framework.

6. The frontend production bundle is currently large.

7. Teacher authentication is demo-style and password storage is plain-text in the current implementation.

---

## 33. What Is Finalized Right Now

As of the current implementation, the following behaviors are finalized in code:

- role-based login
- teacher dashboard
- student dashboard
- legacy upload and evaluation flow
- continuous stage-based flow
- one submission per stage
- chronological stage enforcement
- reverse-chronology deletion
- master brief topic gate
- multi-step LLM evaluation
- anti-hallucination guardrails
- plagiarism similarity for legacy submissions
- stage-wise marks scaling
- final marks as sum of stage marks
- class comparison and rank
- stage-wise marks visibility to student and teacher
- dedicated stage feedback pages
- previous recommendation carry-forward checking

---

## 34. Recommended Reading Order in Code

If you want to understand the project by reading code in a good order:

1. `backend/main.py`
2. `backend/config.py`
3. `backend/models.py`
4. `backend/routes/students.py`
5. `backend/routes/teacher.py`
6. `backend/routes/continuous.py`
7. `backend/rag_pipeline.py`
8. `backend/services/continuous_evaluation.py`
9. `backend/services/grading.py`
10. `backend/services/master_brief.py`
11. `frontend/src/App.jsx`
12. `frontend/src/pages/StudentDashboard.jsx`
13. `frontend/src/pages/TeacherDashboard.jsx`
14. `frontend/src/pages/StageFeedbackPage.jsx`

---

## 35. Quick Mental Model

If you want the shortest accurate mental model of the system:

- PostgreSQL stores the truth
- FAISS stores retrieval data for legacy submissions
- Gemini is called through an OpenAI-compatible client
- evaluation is multi-step and JSON-driven
- stage submissions are now the primary workflow
- each stage has its own marks
- final marks are the sum of the latest stage marks
- the class comparison is mathematical
- rank is stored
- letter grades are not used in the UI
