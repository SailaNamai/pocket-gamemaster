### Warning for the faint of heart (should be, hopefully hard mode only)
## Example:

You are Roy: A 9-year-old boy who has been living alone in Prague's ruins after his parents left to scavenge food three days ago. They never returned. The world is dark now: The streets once alive with tourists are deserted, littered with abandoned trams, burned-out cars, and barricades long since overrun by the undead hordes that roam this land. Nobody knows how or why civilization collapsed; only that it did in a matter of days. Some say it was biological warfare gone wrong while others claim a mutated virus brought humanity to its knees. You've been surviving on your own for weeks now, relying on scraps and whatever you can scavenge from abandoned buildings. Your parents left three days ago with promises they'd return soon but the silence has grown deafening. Hunger won out over fear today so here you are: wandering through Prague's desolate streets in search of food. As you turn a corner onto Wenceslas Square, your eyes widen at what lies before you - hundreds upon thousands of undead shuffling aimlessly about like mindless cattle. Their moans fill the air as they sense your presence and begin to move towards you with an unnatural speed that belies their otherwise sluggish demeanor.

> Raise my fists, yodel and charge them.
```console
"Effect":       "You raise your fists and let out a loud yodel, 
                then charge towards the horde."
"Consequence":  "The zombies are momentarily startled by your
                sudden outburst and movement, but quickly regain 
                their composure and begin to close in on you."
"Stat Update":  Health (no change, unharmed), 
                Stamina (slightly depleted, now 75%), 
                Fear (slightly increasing, now anxious)
"Judgement":    Partial Failure
"Reasoning":    Your unorthodox approach momentarily distracts the zombies, 
                but they quickly recover and continue their relentless pursuit. 
                Your yodeling and charging may have bought you a few seconds, 
                but it's not enough to deter the sheer number of undead closing in on you.
```
You raise your fists high into the air as if preparing for battle, let out an ear-piercing yelp that echoes through Wenceslas Square - "Yeeeee-haw!" You then charge forward with reckless abandon towards the sea of mindless flesh before you. The zombies are momentarily startled by your sudden outburst and movement. Their moans falter as they turn their heads in unison to face this new threat, but only for a brief moment. The sheer number of undead quickly regains its composure - thousands upon thousands of them continue shuffling towards you with an unnatural speed that belies their otherwise sluggish demeanor.

> Punch them in the face.
```console
"Effect":       "You throw a punch at a zombie's face."
"Consequence":  "Your fist connects with the zombie's jaw, 
                but it barely reacts."
"Stat Update":  Health (no change, unharmed), 
                Stamina (slightly depleted, now 80%), 
                Fear (slightly increasing, now anxious).
"Judgement":    Partial Failure
"Reasoning":    Your punch is effective but the zombie's lack of reaction suggests 
                it's already too far gone to feel pain or fear, 
                and the sheer number of undead continues to close in.
```
As your fist connects with the zombie's jaw, you can't help but notice how utterly unresponsive they are. The blow barely seems to register; their eyes remain vacant as they continue shuffling towards you like a mindless automaton. You realize that even if you manage to land more hits, it won't make much of an impact on these creatures - your only hope lies in evading them or finding some other means of escape. You throw another punch at the next zombie's face but again receive no reaction beyond their relentless forward motion. The sheer number of undead continues to close in around you and panic begins to set in as you realize just how outnumbered you are. Your heart races, pounding against your ribcage like a wild animal trying to escape its cage.

> I don't stop punching.
```console
"Effect":       "You continue punching the zombies, 
                but they just keep coming."
"Consequence":  "The zombies keep shuffling towards you, 
                seemingly unaffected by your blows."
"Stat Update":  Health (decreasing, now injured)
                Stamina (decreasing, now exhausted)
"Judgement":    Partial Failure.
"Reasoning":    The action of punching zombies is highly unlikely to succeed 
                in this scenario due to the sheer number of undead and their relentless approach. 
                Additionally, the physical toll of continuous punching without proper defense is significant.
```
You continue your futile assault on the hordes before you - each punch landing with a sickening thud against lifeless flesh that refuses to yield an inch. The zombies keep shuffling towards you like mindless cattle, their moans growing louder as they close in from all sides. Your fists ache and bleed but still you persist; driven by desperation rather than any hope of success. The sheer number of undead continues its relentless march forward - a seemingly endless tide of rotting flesh that threatens to engulf you whole. You stumble backwards under the weight of their numbers, your breath coming in ragged gasps as exhaustion begins to set in. The zombies press closer now, their cold dead hands reaching out for you like grasping fingers from beyond the grave.

> Try to get away.
```console
"Effect":       "You attempt to run away from the zombies."
"Consequence":  "The zombies pursue you relentlessly."
"Stat Update":  "Health (depleted, now dead)."
"Judgement":    "Critical Failure"
"Reasoning":    "The zombies are too numerous and too close for you to escape. 
                Your attempt to run only serves to draw their attention further, 
                and they quickly overwhelm you."
```
You turn around in a desperate bid for freedom but it's already too late - the hordes of undead have your scent now and will not be deterred from their prey so easily. Their moans grow louder as they close in on all sides like an unstoppable tide, driven by insatiable hunger that knows no bounds. You try to run faster but with every step you feel hands grasping for you - cold dead fingers clawing at your clothes and flesh alike. As the zombies pull you down into their ranks, a sickening feeling washes over you as teeth sink deep into your tender skin. The pain is unimaginable yet somehow it seems distant; like watching someone else suffer from afar while you remain trapped in this waking nightmare that refuses to end. Your vision begins to blur and fade around the edges - darkness closing in on all sides with an almost palpable force.

> I let it end.
```console
"Effect":       "None (no change in environment)."
"Consequence":  "None (situation advances naturally)."
"Stat Update":  "Health (depleted, now dead)."
"Judgement":    "Critical Failure"
"Reasoning":    "The player character, Roy, attempts to escape the zombie horde 
                but is overwhelmed and consumed by them. 
                This is a Critical Failure because it results in the worst possible outcome for the character."
```
You stand frozen with fear as you watch your life slip away before your very eyes - their cold dead hands grasping at you like vultures circling their prey, waiting to tear flesh from bone. The pain is indescribable yet somehow it seems distant; like watching someone else suffer from afar while you remain trapped in this waking nightmare that refuses to end. The darkness closes in around the edges of your vision as teeth sink deeper into tender skin - a sickening feeling washing over you with each passing moment. You can hear their moans growing louder and more urgent, driven by an insatiable hunger that knows no bounds. The last thing you see is a sea of rotting flesh closing in on all sides before everything goes black. **GAME OVER** Try again?

## Deathloop:
Its possible to be stuck in a deathloop because the LLM keeps emitting more than two paragraphs and doesn't have the token budget to actually finish the job. Your continues will however never make the situation better - always fail/critical fail... "Let it end" should break the loop or just start a new game.
