
##### Important
## 1: (further improved - observing) narrative drift/degradation
## 1: 2nd person pov breaking

## 2: (solved - observing) tag json looks solid now
# Note: When the json was broken it was easy to filter out player from character... 
# Note: now that it gets it right i need to think about determining who the player is... that skews the rating - always present.
- location: disallow partial scoring for unknown, abandoned? - that kind of fluff

## 3: (do) Think about a reddit post
- readme.md requires install instruction
- I don't have a git account
- I do now - upload successful
- https://www.reddit.com/r/LocalLLM/ ?

## 4: (do) It's really hard to kill Roy
- It's not that the GM doesn't decide it...
- It's like taking action works like a keep "alive ping"
- Maybe something like: Don't unnecessarily extend... hm
- Or: Resolve as critical failure if: overwhelming odds against...

## 5: (observe)

## 6: (solved)

---

##### Don't fix?
## -1. We clean the tags constantly instead of persisting our cleaned version into DB
Makes little difference from a performance perspective

## 0. User parameters too big
Insanely long user parameters will reduce long-term memory budget to 0.
Might push the system prompts out of context.

## 1. 

## 2. (could be solved - observing)
If the user clicks continue often the LLM will generate a player action to advance the narrative.
Mostly its just putting questions or minor actions into a player tag. Narratively I think it would be okay under continue...
DB doesn't reflect it as a player action and the summarize pipeline is capable of dealing with multiple player tags per slice...
That means it'll just get summarized away and most likely tagged as medium...
Could scrub the tag in the front end if it happens. Keep it as a crutch for the LLM...
Might have to scrub in backend...
PlayerActionI ask about Mrs. Jenkins./PlayerAction
As the silence between Jed and Emily is broken by the crackling of the fire, Emily closes the cookbook and looks up at you with a soft expression.

Might even turn that into a proper action... Its correctly written in I, the paragraph still in you.
I could cheat that in the front end... make two paragraphs out of it. p-data with player action.
That should push it into the DB. I have no idea what happens when we add an id in between two ids like 50,51...
That could be seriously annoying.
# Note: Gotta find out anyway, people might add paragraphs anywhere.
Ok, so that inserts cleanly already - no issue then.
If I leave the PlayerAction tag in the DB it'll propagate as allowed writing style inside a paragraph...
Allow the behaviour, catch in front end, turn in two paragraphs, then push back to db
(already overwrites changes - might have to check if the automated input is caught by the candidate dif calc or push won't fire)
If the player is confronted with an action that he didn't take? ... yeah, no.
Can scrub it and change 1st to 2nd person. You ask about Mrs. Jenkins. As the silence between...
2nd person then gets passed as an edit to DB and removes the tag there.
You stop when a PlayerAction.../PlayerAction would be required.
It's because of this part of the instruction.
It thinks it can't continue without the needed action so it makes one. Removing it would have it overshoot again.
It might not even think it needs a player action. 
It might just think it needs an action every 1 or 2 paragraphs because that's the structure I've been feeding it...
Hm: 
You stop when a PlayerAction.../PlayerAction would be narratively required.

PlayerActionI watch them silently while they examine my supplies./PlayerAction As Jed and Emily continue to sort through the meager provisions I brought from Mrs. Jenkins' home, their quiet...

Ok - probably best to change the continue one (action can stay, because its always given an action...)
You do not act for the player. You stop when a PlayerAction.../PlayerAction would be required.

Gotta be careful
1: don't make it constantly advance the narrative with hallucinations, let the player decide.
2: have it still stop writing when the player should act.
You do not act for the player and stop when player input would be required.
Might think about the entire system prompt. I have a writer thats not allowed to advance his book using the protagonist?
Ok, changed prompt:
- You never decide or describe what the player does, thinks, or says. 
- You only describe the world, other characters, and the unfolding situation around the player.