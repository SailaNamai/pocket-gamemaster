
##### Important
## 1: (solved)

## 2: (do) tag json looks solid now
# Note: When the json was broken it was easy to filter out player from character... now that it gets it right i need to think about determining who the player is... that skews the rating - always present.
- location: disallow partial scoring for unknown, abandoned? - that kind of fluff
- filter any "(text)" from character tags
- tag recent has no player tag wrap

## 3: (do) readme.md requires install instruction (git).
I don't have a git account

## 4: (do) Response length inflation - when the story grows?
It begins reasonable but paragraphs on occassion begin to bust the 350 limit.
Possible causes:
- additional context it wants to incorporate
- weakening adherence to the first part of the prompt, when enough memories are added.
Possible solution:
- Stronger guard rails - those are pretty explicit already
- Fall back to only taking the 1st paragraph - pacing issues
- Revisit the whole 6 paragraph approach: Think about how the story would unfold in the next n paragraphs and then write the next one. - could work...
- Re-feed the system prompt at the end (Remember: You are...) - feels dirty, would like to avoid, also ~100 tokens

## 5: (solved) 

## 6: (solved)

---

##### Don't fix?
## -1. We clean the tags constantly instead of persisting our cleaned version into DB
Makes little difference from a performance difference

## 0. User parameters too big
Insanely long user parameters will reduce long-term memory budget to 0.
Might push the system prompts out of context.

## 1. (unsure if still relevant) LLM finishes with What will you do next?
- The woman's gaze drifts upwards from her feet, her eyes focusing on yours as she struggles to respond. A faint crease forms between her eyebrows as she winces in pain with each step, yet a spark of determination ignites within those sunken depths when you ask about finding help. "Not... much," she manages to stammer out, her voice hoarse and barely audible over the growing cacophony behind you both. "Main Street's all but abandoned... few scattered survivors here and there." She pauses, swallowing hard as a fresh wave of pain crosses her face before continuing in a low tone: "But I know someone who might be able to help us - my friend Marcus lives on Elm Street, just two blocks from here. He's got experience with the dead... if we can make it that far." As she finishes speaking, you glance back and see that the zombies are mere feet away now, their slow but relentless shamble a stark reminder of how little time you have to act. You spot a dumpster nearby, its metal lid askew - could it serve as an impromptu shield if needed? The alleyway's entrance beckons just ahead, promising potential shelter from the horde behind. What will you do next?

I think it's okay to let this slide, and it fits well here.


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
Note: Gotta find out anyway, people might add paragraphs anywhere.
Ok, so that inserts cleanly already - no issue then.
If I leave the PlayerAction tag in the DB it'll propagate as allowed writing style inside a paragraph...
Allow the behaviour, catch in front end, turn in two paragraphs, then push back to db
(already overwrites changes - might have to check if the automated input is caught by the candidate dif calc or push won't fire)
If the player is confronted with an action that he didn't take? ... yeah, no.
Can scrub it and change 1st to 2nd person. You ask about Mrs. Jenkins. As the silence between...
2nd person then gets passed as an edit to DB and removes the tag there.
You stop when a PlayerAction.../PlayerAction would be required.
 Its because of this part of the instruction.
It thinks it can't continue without the needed action so it makes one. Removing it would have it overshoot again.
It might not even think it needs a player action. It might just think it needs an action every 1 or 2 paragraphs because thats the structure I've been feeding it...
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