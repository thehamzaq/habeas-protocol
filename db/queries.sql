-- Sample queries against the habeas-protocol corpus.
-- Connect with: ./scripts/postgres_local.sh psql

-- =====================================================================
-- A. CORPUS HEALTH
-- =====================================================================

-- 1. Per-tribunal counts (should match the dashboard headline).
SELECT tribunal_code, count(*) AS n
FROM judgments
GROUP BY tribunal_code
ORDER BY tribunal_code;

-- 2. Documents on disk, by tribunal × content type.
SELECT tribunal_code, content_type, count(*), pg_size_pretty(sum(file_size_bytes)) AS total_bytes
FROM documents
GROUP BY 1, 2
ORDER BY 1, 2;

-- 3. How many raw files matched a structured judgment automatically?
SELECT
  tribunal_code,
  count(*)                                AS docs,
  count(judgment_id)                      AS linked,
  count(*) - count(judgment_id)           AS unlinked
FROM documents
GROUP BY tribunal_code
ORDER BY tribunal_code;

-- =====================================================================
-- B. PRIMITIVES — reproduce the paper's headline numbers
-- =====================================================================

-- 4. Mean v0.2 primitive score per tribunal.
SELECT tribunal_code, n_judgments,
       round(mean_pr_score::numeric, 2) AS mean_pr,
       round(mean_sp_score::numeric, 2) AS mean_sp
FROM tribunal_means_v02
ORDER BY mean_pr DESC NULLS LAST;

-- 5. Per-primitive mean (v0.2) per tribunal — heatmap source.
SELECT j.tribunal_code,
       s.primitive,
       round(avg(s.score)::numeric, 2) AS mean_score,
       count(*) AS n
FROM judgments j
JOIN primitive_scores s ON s.judgment_id = j.id AND s.version = 'v02'
GROUP BY 1, 2
ORDER BY 1, 2;

-- 6. Saturation check: does mean PR score change as we expand the ADGM sample?
WITH ranked AS (
  SELECT j.id,
         row_number() OVER (PARTITION BY j.tribunal_code ORDER BY j.date_issued NULLS LAST, j.id) AS rn
  FROM judgments j
  WHERE j.tribunal_code = 'ADGM'
)
SELECT
  CASE WHEN rn <= 7  THEN 'first_7'
       WHEN rn <= 16 THEN 'first_16'
       ELSE                'all_76'
  END AS slice,
  round(avg(s.score)::numeric, 3) AS mean_pr_score
FROM ranked r
JOIN primitive_scores s ON s.judgment_id = r.id
WHERE s.version = 'v02' AND s.primitive IN ('PR1','PR2','PR3','PR4','PR5','PR6')
GROUP BY 1
ORDER BY 1;

-- =====================================================================
-- C. RULE FREQUENCY
-- =====================================================================

-- 7. Top-cited instruments across the gold set + AI-coded corpus.
SELECT instrument, n_judgments, n_difc, n_adgm, n_sicc
FROM rule_frequency
LIMIT 20;

-- 8. Rules unique to a single tribunal.
SELECT instrument, n_difc, n_adgm, n_sicc, n_judgments
FROM rule_frequency
WHERE (CASE WHEN n_difc > 0 THEN 1 ELSE 0 END
       + CASE WHEN n_adgm > 0 THEN 1 ELSE 0 END
       + CASE WHEN n_sicc > 0 THEN 1 ELSE 0 END) = 1
ORDER BY n_judgments DESC;

-- =====================================================================
-- D. CORPUS QUERIES (raw bytes + structured layer joined)
-- =====================================================================

-- 9. Find the trace cases by case_no (these are the five working traces).
SELECT j.case_no, j.tribunal_code, j.date_issued,
       j.parties_claimant, j.parties_defendant, j.judge,
       (SELECT count(*) FROM documents d WHERE d.judgment_id = j.id) AS docs
FROM judgments j
WHERE j.case_no IN (
  'CFI 058/2024',         -- trace 1
  'ARB 008/2026',         -- trace 2
  'ENF 271/2025',         -- trace 3
  'ADGMCFI-2024-320',     -- trace 4
  'ADGMCFI-2024-158'      -- trace 5
)
ORDER BY j.case_no;

-- 10. Full-text search over the raw bytes. Find every doc mentioning
-- "indemnity basis" anywhere in its extracted text.
SELECT tribunal_code, filename, judgment_id,
       ts_rank(to_tsvector('english', text_extracted),
               plainto_tsquery('english', 'indemnity basis costs')) AS rank
FROM documents
WHERE to_tsvector('english', coalesce(text_extracted, ''))
      @@ plainto_tsquery('english', 'indemnity basis costs')
ORDER BY rank DESC
LIMIT 10;

-- 11. Show the gold-set entries (39 judgments graded first-pass by LLM, not by hand).
SELECT case_no, tribunal_code, date_issued, claim_type, operative_amount_aed
FROM judgments
WHERE gold_set
ORDER BY tribunal_code, date_issued;

-- 12. ADGM contract disputes (the cross-border SaaS lane).
SELECT j.case_no, j.date_issued, j.judge,
       j.parties_claimant || ' v ' || j.parties_defendant AS parties,
       coalesce(d.filename, '(no raw file)') AS raw_file
FROM judgments j
LEFT JOIN documents d ON d.judgment_id = j.id AND d.content_type = 'pdf'
WHERE j.tribunal_code = 'ADGM'
  AND j.claim_type IN ('contract_dispute', 'contract_breach', 'contract')
ORDER BY j.date_issued DESC NULLS LAST;

-- =====================================================================
-- E. THESIS-RELEVANT SLICES
-- =====================================================================

-- 13. Cross-border SaaS / AI / stablecoin dispute markers
-- (free-text search over the raw bytes for the verticals the paper targets).
SELECT j.tribunal_code, j.case_no, j.date_issued,
       length(d.text_extracted) AS doc_chars
FROM documents d
JOIN judgments j ON j.id = d.judgment_id
WHERE to_tsvector('english', d.text_extracted)
      @@ plainto_tsquery('english', 'source code software development platform')
ORDER BY j.date_issued DESC NULLS LAST
LIMIT 10;

-- 14. Each judge's "ruling style" — mean per-primitive score per judge,
-- limited to judges with ≥ 3 coded judgments.
SELECT
  j.judge,
  count(DISTINCT j.id) AS n,
  round(avg(s.score)::numeric, 2) AS mean_pr_score
FROM judgments j
JOIN primitive_scores s ON s.judgment_id = j.id
WHERE s.version = 'v02' AND s.primitive LIKE 'PR%' AND j.judge IS NOT NULL
GROUP BY j.judge
HAVING count(DISTINCT j.id) >= 3
ORDER BY mean_pr_score DESC;

-- 15. Operative amount distribution by tribunal (where coded).
SELECT j.tribunal_code,
       count(*)                                                    AS n,
       count(operative_amount_aed)                                 AS n_with_amount,
       round(avg(operative_amount_aed)::numeric, 0)                AS mean_aed,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY operative_amount_aed) AS median_aed,
       max(operative_amount_aed)                                   AS max_aed
FROM judgments j
GROUP BY 1
ORDER BY 1;
