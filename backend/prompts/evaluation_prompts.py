import json


RAG_EVALUATION_QUERY = (
    "Evaluate the project for innovation, technologies used, complexity, technical depth, "
    "clarity, impact, weaknesses, evidence quality, and future scope."
)

COMMON_GUARDRAILS = """
You are evaluating a student course project.

Rules:
- ONLY use the provided project content.
- If information is missing, return the literal text "Insufficient data".
- Never fabricate technologies, metrics, outcomes, datasets, or implementation details.
- Use retrieved chunks only.
- Return valid JSON only with no markdown fences.
""".strip()

FEATURE_EXTRACTION_SYSTEM_PROMPT = f"""
{COMMON_GUARDRAILS}

Task:
1. Extract project innovation evidence.
2. Extract technologies used exactly as stated.
3. Estimate complexity only from provided evidence.
4. Attach evidence chunk ids for every conclusion.
""".strip()

SCORING_SYSTEM_PROMPT = f"""
{COMMON_GUARDRAILS}

Task:
1. Score each criterion from 1 to 10.
2. Justify each score with evidence-based reasoning.
3. If evidence is weak or missing, lower the score and say "Insufficient data".
""".strip()

FEEDBACK_SYSTEM_PROMPT = f"""
{COMMON_GUARDRAILS}

Task:
1. Generate actionable strengths, weaknesses, suggestions, and future scope.
2. Highlight weak sections by referencing chunk ids tied to lower scores.
3. Keep feedback constructive and specific to the evidence.
""".strip()


def build_chunk_context(chunks: list[dict]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        parts.append(
            "\n".join(
                [
                    f"chunk_id: {chunk['chunk_id']}",
                    f"retrieval_score: {chunk.get('score', 0.0)}",
                    "content:",
                    chunk["text"],
                ]
            )
        )
    return "\n\n".join(parts)


def build_feature_extraction_prompt(chunks: list[dict]) -> str:
    return f"""
Retrieved project chunks:
{build_chunk_context(chunks)}

Return JSON with this exact top-level structure:
{{
  "innovation": {{
    "summary": "string or Insufficient data",
    "evidence_chunk_ids": [0]
  }},
  "technologies": ["technology 1", "technology 2"],
  "complexity": {{
    "summary": "string or Insufficient data",
    "level": "low | medium | high | Insufficient data",
    "evidence_chunk_ids": [0]
  }}
}}
""".strip()

def _build_rubric_prompt_rows(rubrics: list[dict]) -> str:
    rows: list[str] = []
    for rubric in rubrics:
        rows.append(
            f'- key: "{rubric["key"]}", name: "{rubric["name"]}", weight: {rubric["weight"]}'
        )
    return "\n".join(rows)


def build_scoring_prompt(chunks: list[dict], features: dict, rubrics: list[dict]) -> str:
    feature_json = json.dumps(features, indent=2)
    rubric_examples = ",\n    ".join(f'"{rubric["key"]}": 1' for rubric in rubrics)
    justification_examples = ",\n    ".join(f'"{rubric["key"]}": "string"' for rubric in rubrics)
    evidence_examples = ",\n    ".join(f'"{rubric["key"]}": [0]' for rubric in rubrics)
    return f"""
Retrieved project chunks:
{build_chunk_context(chunks)}

Extracted features:
{feature_json}

Scoring rubrics to use:
{_build_rubric_prompt_rows(rubrics)}

Important:
- Score only the rubric keys listed above.
- Every rubric score must be from 1 to 10.
- Do not invent extra rubric keys.

Return JSON with this exact structure:
{{
  "criterion_scores": {{
    {rubric_examples}
  }},
  "criterion_justifications": {{
    {justification_examples}
  }},
  "evidence": {{
    {evidence_examples}
  }}
}}
""".strip()


def build_feedback_prompt(chunks: list[dict], features: dict, scores: dict) -> str:
    feature_json = json.dumps(features, indent=2)
    score_json = json.dumps(scores, indent=2)
    return f"""
Retrieved project chunks:
{build_chunk_context(chunks)}

Extracted features:
{feature_json}

Scoring output:
{score_json}

Return JSON with this exact structure:
{{
  "strengths": ["string"],
  "weaknesses": ["string"],
  "suggestions": ["string"],
  "future_scope": ["string"],
  "weak_sections": [
    {{
      "criterion": "rubric key from criterion_scores",
      "chunk_id": 0,
      "reason": "string"
    }}
  ]
}}
""".strip()
