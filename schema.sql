-- Racing Intelligence: proposed common national schema (pilot version, DuckDB)
-- Principles: one row per real-world thing; every value traceable to a source retrieval;
-- download time (retrieved_at) is never treated as the time information became known (knowable_at).

CREATE TABLE source (
  source_id            TEXT PRIMARY KEY,   -- e.g. RQ_SECTIONAL_CSV, BETFAIR_MONTHLY
  publisher            TEXT,
  description          TEXT,
  automation_permitted TEXT,               -- yes | unconfirmed | no
  storage_permitted    TEXT,               -- yes | unconfirmed | no
  sharing_permitted    TEXT,               -- derived_only | unconfirmed | no
  licence_note         TEXT,
  url                  TEXT
);

CREATE TABLE retrieval (
  retrieval_id        TEXT PRIMARY KEY,
  source_id           TEXT REFERENCES source(source_id),
  url                 TEXT,
  method              TEXT,                -- file_download | web_fetch_transcription | manual_capture
  exact_copy          BOOLEAN,             -- false for transcriptions
  retrieved_at        TIMESTAMP,           -- when WE got it
  publisher_timestamp TIMESTAMP,           -- when the publisher says it was issued (often unknown)
  sha256              TEXT,                -- hash of the file as served
  source_bytes        BIGINT,
  local_file          TEXT,                -- what we kept (exact copy or extract)
  local_sha256        TEXT,                -- hash of what we kept
  note                TEXT
);

CREATE TABLE venue (
  venue_id       TEXT PRIMARY KEY,         -- e.g. QLD-EAGLE-FARM
  state          TEXT,
  canonical_name TEXT,
  club           TEXT
);

CREATE TABLE venue_alias (
  source_id TEXT,
  alias     TEXT,                          -- the name or code a source uses
  venue_id  TEXT REFERENCES venue(venue_id),
  PRIMARY KEY (source_id, alias)
);

CREATE TABLE meeting (
  meeting_id   TEXT PRIMARY KEY,           -- YYYYMMDD-venue_id
  meeting_date DATE,
  venue_id     TEXT REFERENCES venue(venue_id),
  category     TEXT,                       -- metro | provincial | country
  surface      TEXT,
  rail         TEXT,
  weather      TEXT
);

CREATE TABLE race (
  race_id               TEXT PRIMARY KEY,  -- meeting_id-Rn
  meeting_id            TEXT REFERENCES meeting(meeting_id),
  race_no               INTEGER,
  race_name             TEXT,
  distance_m            INTEGER,
  class_raw             TEXT,              -- as published by the official source
  class_code            TEXT,              -- normalised: BM78, CL3, OPEN-HCP, 3YO-HCP, G1, LR ...
  scheduled_start_local TEXT,
  actual_off_local      TEXT,
  prize_total_aud       INTEGER,
  race_time_s           DOUBLE,
  track_rating_at_race  TEXT,             -- rating in force when the race was run (stewards report), not the final page value
  track_rating_tracking TEXT              -- rating carried in the timing provider's file (can lag)
);

CREATE TABLE horse (
  horse_id       TEXT PRIMARY KEY,         -- internal key; never a source's key
  canonical_name TEXT,
  country_suffix TEXT,
  foaling_year   INTEGER,
  sex            TEXT,
  sire           TEXT,
  dam            TEXT
);

CREATE TABLE horse_alias (
  source_id     TEXT,
  source_key    TEXT,                      -- e.g. Betfair SELECTION_ID; NULL when a source has no key
  name_as_given TEXT,
  horse_id      TEXT REFERENCES horse(horse_id),
  match_method  TEXT,                      -- race+saddlecloth+name | name+state+age | manual
  confidence    TEXT,                      -- high | medium | low
  note          TEXT
);

CREATE TABLE starter (                     -- one row per horse entered in a race (scratched included)
  race_id       TEXT REFERENCES race(race_id),
  saddlecloth   INTEGER,
  horse_id      TEXT REFERENCES horse(horse_id),
  barrier       INTEGER,
  weight_kg     DOUBLE,
  jockey        TEXT,
  trainer       TEXT,
  scratched     BOOLEAN,
  emergency     BOOLEAN,
  finish_pos    INTEGER,
  margin_l      DOUBLE,
  finish_time_s DOUBLE,
  dist_run_m    INTEGER,
  first400_s    DOUBLE,
  last600_s     DOUBLE,
  top_kmh       DOUBLE,
  PRIMARY KEY (race_id, saddlecloth)
);

CREATE TABLE sectional (                   -- one row per runner per timing segment
  race_id        TEXT,
  saddlecloth    INTEGER,
  segment_end_m  INTEGER,                  -- metres from the start where the segment ends
  segment_len_m  INTEGER,
  split_s        DOUBLE,
  top_speed_ms   DOUBLE,                   -- verified: max per segment x 3.6 = published TOP KM/H
  avg_speed_ms   DOUBLE,
  ground_m       DOUBLE,                   -- ground actually covered in the segment
  position       INTEGER,                  -- position at the end of the segment
  dist_to_rail_m DOUBLE,
  stride_freq_hz DOUBLE,
  stride_len_m   DOUBLE,
  timing_system  TEXT,                     -- tripleSdata | SwissTiming | ChampionData
  PRIMARY KEY (race_id, saddlecloth, segment_end_m)
);

CREATE TABLE position_in_run (
  race_id        TEXT,
  saddlecloth    INTEGER,
  marker_to_go_m INTEGER,
  position       INTEGER,
  PRIMARY KEY (race_id, saddlecloth, marker_to_go_m)
);

CREATE TABLE outcome_flag (                -- Betfair win/place flags only; price columns are never loaded
  race_id      TEXT,
  saddlecloth  INTEGER,
  source_id    TEXT,
  selection_id TEXT,
  win_flag     BOOLEAN,
  place_flag   BOOLEAN
);

CREATE TABLE field_provenance (            -- point-in-time class for each kind of field, per source
  source_id   TEXT,
  field       TEXT,
  pit_class   TEXT,                        -- PRE_RACE_PUBLISHED | RACE_MORNING | POST_RACE_OUTCOME | RETRO_REVISED | UNVERIFIABLE_TIME
  knowable_at_rule TEXT,                   -- how to derive when the value became known
  note        TEXT
);

CREATE TABLE data_gap (
  state  TEXT,
  entity TEXT,
  field  TEXT,
  reason TEXT,                             -- NOT_PUBLISHED | PERMISSION_REQUIRED | ACCESS_BLOCKED | NOT_TESTED
  detail TEXT
);

CREATE TABLE integrity_check (
  check_id    TEXT,
  scope       TEXT,
  description TEXT,
  expected    TEXT,
  observed    TEXT,
  status      TEXT                         -- PASS | FAIL | FLAG
);
