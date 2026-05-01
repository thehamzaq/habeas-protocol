-- Habeas Protocol corpus schema
-- Postgres 16+
--
-- Two layers:
--   (1) "structured" — the 121 hand/AI-coded judgments from data/judgments.json,
--       with their primitive scores, rules cited, and per-entry coding provenance.
--   (2) "raw" — the scraped corpus on disk (DIFC HTML, ADGM PDFs, SICC HTML),
--       indexed so anyone can query the bytes alongside the structured layer.
--
-- The two layers join via judgments.case_no ↔ documents.case_no_inferred where
-- a parser has matched a raw file to a structured entry; documents without a
-- match are still queryable by tribunal + scrape_date + filename.

BEGIN;

-- ---------------------------------------------------------------------------
-- Reference data
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tribunals (
  code        text PRIMARY KEY,
  full_name   text NOT NULL,
  base_url    text,
  legal_family text  -- 'common_law', 'civil_law_hybrid', etc.
);

INSERT INTO tribunals (code, full_name, base_url, legal_family) VALUES
  ('DIFC', 'DIFC Courts', 'https://www.difccourts.ae', 'common_law'),
  ('ADGM', 'ADGM Courts', 'https://www.adgm.com/adgm-courts', 'common_law_english_via_statute'),
  ('SICC', 'Singapore International Commercial Court', 'https://www.judiciary.gov.sg/sicc', 'common_law')
ON CONFLICT (code) DO UPDATE SET
  full_name    = EXCLUDED.full_name,
  base_url     = EXCLUDED.base_url,
  legal_family = EXCLUDED.legal_family;

CREATE TABLE IF NOT EXISTS primitives (
  code        text PRIMARY KEY,  -- 'PR1'..'PR6', 'SP1', 'SP2'
  kind        text NOT NULL,     -- 'per_ruling' | 'system_property'
  short_label text NOT NULL,
  description text NOT NULL
);

INSERT INTO primitives (code, kind, short_label, description) VALUES
  ('PR1', 'per_ruling', 'Identity',           'Stable per-ruling identifier (case_no, citation, URL).'),
  ('PR2', 'per_ruling', 'Evidence log',       'Typed event log; what happened, in what order, on what proof.'),
  ('PR3', 'per_ruling', 'Rule bind',          'Rule applied is named, versioned, and machine-readable.'),
  ('PR4', 'per_ruling', 'Procedure',          'Procedural state is verifiable from the order.'),
  ('PR5', 'per_ruling', 'Ruling',             'Ruling composes deterministically from the rule + the events.'),
  ('PR6', 'per_ruling', 'Enforcement bridge', 'Ruling states an instrument that another forum can execute.'),
  ('SP1', 'system_property', 'Separation of powers', 'Tribunal is structurally independent of the executive that funds it.'),
  ('SP2', 'system_property', 'Appeal path',          'A higher-instance review route exists and is in fact used.')
ON CONFLICT (code) DO UPDATE SET
  short_label = EXCLUDED.short_label,
  description = EXCLUDED.description;

-- ---------------------------------------------------------------------------
-- Structured layer: hand/AI-coded judgments
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS judgments (
  id                    bigserial PRIMARY KEY,
  tribunal_code         text NOT NULL REFERENCES tribunals(code),
  case_no               text NOT NULL,
  url                   text,
  division              text,
  date_issued           date,
  judge                 text,
  parties_claimant      text,
  parties_defendant     text,
  claim_type            text,
  outcome               text,
  operative_amount_aed  numeric(20, 2),
  neutral_citation      text,
  -- coding provenance
  coder                 text,
  coded_on              date,
  gold_set              boolean DEFAULT false,
  coding_notes          text,
  -- raw row stash (so we never lose info if a column is missing)
  raw_json              jsonb NOT NULL,
  imported_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tribunal_code, case_no)
);

CREATE INDEX IF NOT EXISTS idx_judgments_tribunal     ON judgments(tribunal_code);
CREATE INDEX IF NOT EXISTS idx_judgments_date         ON judgments(date_issued);
CREATE INDEX IF NOT EXISTS idx_judgments_claim_type   ON judgments(claim_type);
CREATE INDEX IF NOT EXISTS idx_judgments_gold_set     ON judgments(gold_set) WHERE gold_set;
CREATE INDEX IF NOT EXISTS idx_judgments_raw_json_gin ON judgments USING gin (raw_json);

-- Per-judgment primitive scores. Two versions live side by side (v01: P1..P7,
-- v02: PR1..PR6 + SP1..SP2). Each row is one (judgment, primitive, version).
CREATE TABLE IF NOT EXISTS primitive_scores (
  judgment_id   bigint  NOT NULL REFERENCES judgments(id) ON DELETE CASCADE,
  version       text    NOT NULL,  -- 'v01' | 'v02'
  primitive     text    NOT NULL,  -- 'PR1', 'P1', etc.
  score         smallint NOT NULL CHECK (score IN (0, 1, 2)),
  PRIMARY KEY (judgment_id, version, primitive)
);

CREATE INDEX IF NOT EXISTS idx_scores_primitive_version ON primitive_scores(primitive, version);

-- Rules cited (instruments + clauses): normalized + many-to-many.
CREATE TABLE IF NOT EXISTS rules_cited (
  id           bigserial PRIMARY KEY,
  instrument   text NOT NULL UNIQUE  -- 'RDC Part 38', 'UAE Civil Code Art. 390', 'Wood v Capita [2017] UKSC 24', etc.
);

CREATE TABLE IF NOT EXISTS judgment_rules (
  judgment_id  bigint NOT NULL REFERENCES judgments(id) ON DELETE CASCADE,
  rule_id      bigint NOT NULL REFERENCES rules_cited(id) ON DELETE CASCADE,
  PRIMARY KEY (judgment_id, rule_id)
);

CREATE INDEX IF NOT EXISTS idx_judgment_rules_rule ON judgment_rules(rule_id);

-- ---------------------------------------------------------------------------
-- Raw layer: scraped documents on disk
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS documents (
  id                bigserial PRIMARY KEY,
  tribunal_code     text NOT NULL REFERENCES tribunals(code),
  content_type      text NOT NULL CHECK (content_type IN ('html', 'pdf', 'text', 'json')),
  -- file location relative to habeas-protocol/ (e.g. data/raw/judgments/foo.html)
  raw_path          text NOT NULL UNIQUE,
  filename          text NOT NULL,
  file_size_bytes   bigint,
  sha256            text,
  -- extracted plaintext (NULL if not extracted; UTF-8)
  text_extracted    text,
  -- if a parser matched this file to a structured judgment, link both ways
  case_no_inferred  text,
  judgment_id       bigint REFERENCES judgments(id) ON DELETE SET NULL,
  scraped_at        timestamptz,
  imported_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_tribunal      ON documents(tribunal_code);
CREATE INDEX IF NOT EXISTS idx_documents_content_type  ON documents(content_type);
CREATE INDEX IF NOT EXISTS idx_documents_judgment      ON documents(judgment_id);
CREATE INDEX IF NOT EXISTS idx_documents_case_no       ON documents(case_no_inferred);
-- Full-text search over extracted text. English unstemmed (judgments mix
-- common-law English with Arabic/legal Latin; default 'english' gets us 80%).
CREATE INDEX IF NOT EXISTS idx_documents_text_fts
  ON documents USING gin (to_tsvector('english', coalesce(text_extracted, '')));

-- ---------------------------------------------------------------------------
-- Convenience views
-- ---------------------------------------------------------------------------

-- Per-tribunal mean primitive score (v02), reproducing the dashboard headline.
CREATE OR REPLACE VIEW tribunal_means_v02 AS
SELECT
  j.tribunal_code,
  count(DISTINCT j.id) AS n_judgments,
  avg(s.score) FILTER (WHERE s.primitive IN ('PR1','PR2','PR3','PR4','PR5','PR6')) AS mean_pr_score,
  avg(s.score) FILTER (WHERE s.primitive IN ('SP1','SP2')) AS mean_sp_score
FROM judgments j
LEFT JOIN primitive_scores s ON s.judgment_id = j.id AND s.version = 'v02'
GROUP BY j.tribunal_code;

-- Rule frequency across the corpus.
CREATE OR REPLACE VIEW rule_frequency AS
SELECT
  r.instrument,
  count(*) AS n_judgments,
  count(*) FILTER (WHERE j.tribunal_code = 'DIFC') AS n_difc,
  count(*) FILTER (WHERE j.tribunal_code = 'ADGM') AS n_adgm,
  count(*) FILTER (WHERE j.tribunal_code = 'SICC') AS n_sicc
FROM rules_cited r
JOIN judgment_rules jr ON jr.rule_id = r.id
JOIN judgments      j  ON j.id = jr.judgment_id
GROUP BY r.instrument
ORDER BY n_judgments DESC;

-- ---------------------------------------------------------------------------
-- Audit log — every /api/rule_run invocation. The "moat" claim from the
-- roadmap: every rule has a provenance trail back to a court judgment, and
-- every run leaves a tamper-evident record of what facts were fed in and
-- what the predicate said. SHA256 of (module, scope, inputs) lets identical
-- runs deduplicate at the application layer when needed.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rule_runs (
  id              bigserial PRIMARY KEY,
  ts              timestamptz NOT NULL DEFAULT now(),
  module          text NOT NULL,
  scope           text NOT NULL,
  inputs          jsonb NOT NULL,
  output          jsonb,
  success         boolean NOT NULL,
  error           text,
  duration_ms     integer,
  inputs_sha256   text NOT NULL,  -- defence-in-depth: surfaces tampered re-runs
  source_label    text            -- optional: 'simulator' / 'playground' / 'authoring' / etc.
);

CREATE INDEX IF NOT EXISTS rule_runs_ts_idx        ON rule_runs (ts DESC);
CREATE INDEX IF NOT EXISTS rule_runs_module_idx    ON rule_runs (module, scope, ts DESC);
CREATE INDEX IF NOT EXISTS rule_runs_sha_idx       ON rule_runs (inputs_sha256);

-- A single row per scraped document with its coded sibling (NULL on no match).
CREATE OR REPLACE VIEW corpus_index AS
SELECT
  d.id            AS document_id,
  d.tribunal_code,
  d.content_type,
  d.raw_path,
  d.case_no_inferred,
  j.case_no       AS structured_case_no,
  j.judge,
  j.date_issued,
  j.gold_set,
  octet_length(coalesce(d.text_extracted, '')) AS text_bytes
FROM documents d
LEFT JOIN judgments j ON j.id = d.judgment_id
ORDER BY d.tribunal_code, d.filename;

COMMIT;
