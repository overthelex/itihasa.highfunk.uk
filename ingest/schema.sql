CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    url         TEXT,
    license     TEXT,
    source_type TEXT,
    pipeline_stage INT,
    status      TEXT DEFAULT 'pending',
    items_count INT DEFAULT 0,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_msg   TEXT
);

CREATE TABLE texts (
    id          SERIAL PRIMARY KEY,
    source_id   INT NOT NULL REFERENCES sources(id),
    external_id TEXT,
    title       TEXT,
    content     TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'sa',
    script      TEXT,
    tradition   TEXT,
    genre       TEXT,
    token_count INT,
    meta        JSONB DEFAULT '{}'
);

CREATE TABLE parallel_pairs (
    id              SERIAL PRIMARY KEY,
    source_id       INT NOT NULL REFERENCES sources(id),
    source_text     TEXT NOT NULL,
    target_text     TEXT NOT NULL,
    source_lang     TEXT DEFAULT 'sa',
    target_lang     TEXT DEFAULT 'en',
    alignment_type  TEXT,
    expansion_ratio REAL,
    pair_type       TEXT,
    text_ref        TEXT,
    meta            JSONB DEFAULT '{}'
);

CREATE TABLE dictionary_entries (
    id              SERIAL PRIMARY KEY,
    source_id       INT NOT NULL REFERENCES sources(id),
    headword        TEXT NOT NULL,
    headword_slp1   TEXT,
    definition      TEXT NOT NULL,
    pos             TEXT,
    domain          TEXT,
    meta            JSONB DEFAULT '{}'
);

CREATE TABLE morphological (
    id          SERIAL PRIMARY KEY,
    source_id   INT NOT NULL REFERENCES sources(id),
    form        TEXT NOT NULL,
    lemma       TEXT NOT NULL,
    unsandhied  TEXT,
    pos         TEXT,
    features    TEXT,
    wordnet_id  TEXT,
    text_ref    TEXT
);

CREATE INDEX idx_texts_source     ON texts(source_id);
CREATE INDEX idx_texts_lang       ON texts(language);
CREATE INDEX idx_texts_tradition  ON texts(tradition);

CREATE INDEX idx_pairs_source     ON parallel_pairs(source_id);
CREATE INDEX idx_pairs_type       ON parallel_pairs(pair_type);

CREATE INDEX idx_dict_hw          ON dictionary_entries(headword);
CREATE INDEX idx_dict_hw_slp1     ON dictionary_entries(headword_slp1);
CREATE INDEX idx_dict_source      ON dictionary_entries(source_id);

CREATE INDEX idx_morph_lemma      ON morphological(lemma);
CREATE INDEX idx_morph_form       ON morphological(form);
CREATE INDEX idx_morph_source     ON morphological(source_id);

CREATE INDEX idx_texts_trgm       ON texts USING gin(title gin_trgm_ops);
CREATE INDEX idx_dict_hw_trgm     ON dictionary_entries USING gin(headword gin_trgm_ops);
