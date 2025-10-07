-- schema.sql

-- Story-wide parameters and settings (singleton)
CREATE TABLE IF NOT EXISTS story_parameters (
  id                       INTEGER PRIMARY KEY CHECK (id = 1),-- always 1, singleton row
  writing_style_hardcode   TEXT,                              -- fixed/default writing style
  prepend_writing_style    TEXT,                              -- prepend for user-selected writing style
  writing_style            TEXT,                              -- user-selected writing style
  world_setting_hardcode   TEXT,                              -- fixed/default world setting
  prepend_world_setting    TEXT,                              -- prepend for user-selected world setting
  world_setting            TEXT,                              -- user-selected world setting
  rules_hardcode           TEXT,                              -- fixed/default game rules
  prepend_rules            TEXT,                              -- prepend for user-selected game rules
  rules                    TEXT,                              -- user-selected game rules
  player_hardcode          TEXT,                              -- fixed/default player profile
  prepend_player           TEXT,                              -- prepend for user-provided player profile
  player                   TEXT,                              -- user-provided player profile
  characters_hardcode      TEXT,                              -- fixed/default NPC list
  prepend_characters       TEXT,                              -- prepend for user-updated NPC list
  characters               TEXT,                              -- user-updated NPC list
  token_cost               TEXT                               -- token cost for hardcodes and player inputs
);

-- Memory buffers (singleton)
CREATE TABLE IF NOT EXISTS memory (
  id                        INTEGER PRIMARY KEY CHECK (id = 1), -- always 1, singleton row
  mid_memory_hardcode       TEXT,                               -- intermediate “hardcoded” memory
  long_memory_hardcode      TEXT,                               -- long-term “hardcoded” memory
  token_cost                TEXT                                -- token cost for mid- and long-term memories
);

-- User defined token budget (singleton)
CREATE TABLE IF NOT EXISTS token_budget (
  id                        INTEGER PRIMARY KEY CHECK (id = 1), -- always 1, singleton row
  budget_max                INTEGER,                               -- N_CTX
  recent_budget             INTEGER,                               -- tc_budget_recent_paragraphs
  mid_budget                INTEGER,                               -- tc_budget_mid_memories
  long_budget               INTEGER                                -- tc_budget_long_memories
);

-- Summarize_parameters (singleton)
CREATE TABLE IF NOT EXISTS mid_memory_bucket (
  id                              INTEGER PRIMARY KEY CHECK(id = 1), -- always 1, singleton row
  summary_style_hardcode          TEXT,      -- prepend like Summary Writing Style:
  summary_style                   TEXT,      -- Define tagging system
  rules_hardcode                  TEXT,      -- prepend like Weighting Rules:(not so sure about this one)
  rules                           TEXT,      -- rules for determining what are important memories
  tagging_hardcode                TEXT,      -- rules for tagging system
  token_cost                      TEXT       -- cost for all hardcodes + user inputs
);

-- Stored system prompts for different story actions (singleton)
CREATE TABLE IF NOT EXISTS system_prompts (
  id                   INTEGER PRIMARY KEY CHECK (id = 1), -- always 1, singleton row
  story_new            TEXT,                               -- system prompt for starting new story
  sn_token_cost        TEXT,                               -- token cost for story_new
  story_continue       TEXT,                               -- system prompt for continuing story
  sc_token_cost        TEXT,                               -- token cost for story_continue
  story_player_action  TEXT,                               -- system prompt for player actions
  sp_token_cost        TEXT,                               -- token cost for story_player_action
  story_summarize      TEXT,                               -- system prompt for summarization from player action
  ss_token_cost        TEXT,                               -- token cost for story_summarize
  mid_memory_summarize TEXT,                               -- system prompt for summarization of a mid-term memory
  mm_token_cost        TEXT,                               -- token cost for mid_memory_summarize
  tag_generator        TEXT,                               -- system prompt for tagging system
  tg_token_cost        TEXT                                -- token cost for tag_generator
);

-- Sequence of paragraphs for any story phase (intro, continuation, etc.)
CREATE TABLE IF NOT EXISTS story_paragraphs (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,   -- unique paragraph identifier
  story_id            TEXT    NOT NULL,                    -- e.g. 'new', 'continue', 'action'
  paragraph_index     INTEGER NOT NULL,                    -- unique story_id identifier (1, 2, 3, …)
  content             TEXT    NOT NULL,                    -- the actual paragraph text
  token_cost          TEXT    NOT NULL,                    -- token cost for max_prompt_size
  summary             TEXT,                                -- summary
  summary_from_action TEXT,                                -- summary from user action to (but not including) next user action
  summary_token_cost  TEXT,                                -- summary token cost for either summary_from_action or summary
  tags                TEXT,                                -- json
  tags_recent         TEXT,                                -- json - tags from last n paragraphs for tag comparison
  created_at          TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%f','now','localtime')) -- timestamp of insertion
);