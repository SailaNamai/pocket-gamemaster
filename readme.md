# Pocket GameMaster

**PGM** is a free, open source, locally run, text based, multi-personality LLM powered, curated RPG with human-like memory pipeline and a relevance scored, weighed, tag based long-term memory.

It is designed to extend context length as far as I can push it. It is beta and there is still some potential left but currently PGM achieves (~6-10):1 compression ratios and then selects salient memories.
It gives you vast parameter control over story and style. You can edit/add/delete any "memory" on the fly.
Let's unpack that ;)

## - Installation
```console
git clone https://github.com/SailaNamai/pocket-gamemaster.git pgm
```
Find extensive install instructions at
```console
...pgm/documentation/documentation.html
```
---
## - Features
- **Locally run:**
It doesn't need an internet connection. It doesn't communicate with anything and everything is stored locally.

- **Text based, LLM powered:**
Pretty self-explanatory. The LLM is "abliterated" - meaning you should never see:
"As an LLM I'm not able to continue this conversation."

- **Curated:**
We have a GameMaster analyze attempted player actions for its outcome (success/failure, effect...)
That result is then passed to the "writer" persona to generate new text.

- **Human-like memory:**
When we continue the story we feed the LLM as much context as possible:
  - First the detailed, "raw" story (what you read).
  - After a while the raw story is summarized from player action to (but not including) the next player action.
  These mid-term memories mean we remember what's important: What you did and what happened because of it.
  - Mid-term memories are eventually condensed further into long-term memories.
  Long term memories are selectively chosen by relevance and weighed, assembled into chronological order and given to the LLM.

- **"Multiple personalities":**
The LLM is (possibly) prompted a total of five times per "generation" for
  - generate (new, with and without player action),
  - summarize from player action,
  - create tags for that player action,
  - summarize mid-term memories,
  - create tags for the most recent story.
  
  In order to achieve that we let a stage director persona react to player actions, a journalist write the summaries, etc.
  It also returns the result of generate() immediately and then does its thing in the background while you read.
- **Delete/Edit/Add:**
  - Any change you make in the story history, long- and mid-term memories (over)writes to the DB.
  It's pushed when you take an action, before that you can revert with CTRL+Z or F5.
  - I've put the "hard-coded" stuff into .../pgm/services/prompts_*.py
  Making a change here is as simple as modifying a text document (requires app.py to be re-run).

