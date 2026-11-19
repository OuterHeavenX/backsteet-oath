# First-time playtest kit (five players)

**Status: not yet run.** Nobody has playtested this build. Every "target" below is a hypothesis to check, not a
result. Fill in the observation sheets by watching real people; do not infer results from the automated bot.

## What this test is for
The polish pass changed how the opening teaches, how fights read, and what the town shows after you help it. This
test checks whether those changes work for people who have never seen the game.

Questions, in priority order:
1. Do new players understand what to do in the first two minutes without help?
2. Do they discover guarding, throwing, eating and their first technique by themselves?
3. When they get hit or knocked out, can they say why?
4. Do they notice that the Old Quarter changed after Duke, and can they say what caused it?
5. Where do they get lost, bored, frustrated or delighted?
6. Does it run acceptably on their device?

## Who and how long
- Five people who have not played or watched the game. A mix is better than five genre fans: aim for at least two
  who rarely play action games and one who plays on a phone.
- One session each, 30 to 40 minutes: about 25 minutes of play (new game through Duke Brannigan and the first
  street of the Canal Market), then a 10 minute conversation.
- One facilitator who watches and takes notes. Do not play for them or point at the screen.

## Setup (per session, 3 minutes)
1. Use the build from `release/` for this branch (see `docs/polish/VALIDATION_REPORT.md` for launch steps), or the
   web build in a desktop or phone browser. Note which.
2. Title screen: start a **new game in an empty slot**. (If all three slots are used, export or delete one first.)
3. Pause > Settings: turn **Playtest log: On** and **Show FPS: On**. Leave everything else at its default, including
   Control hints and difficulty. Close the menu.
4. Sound on, at a comfortable level. Headphones if the room is noisy.
5. Start a timer when the player first has control (after the opening lines).

The playtest log records, on that device only and inside that save: when things first happened (first move, hit,
block, throw, door, meal, technique, purchase, knockout), which tips were completed by doing and which were
skipped, when each story stage was reached, knockouts per room, and purchases. Read it under
**Pause > Help & tips > Playtest notes**. Nothing is sent anywhere. Turn it off afterwards if the device is the player's own.

## Facilitator script
Read this aloud, then stay quiet.

> "Thanks for doing this. This is a game that is still being made, and I'm testing the game, not you. Nothing
> you do is wrong. If something is confusing, that is exactly what I need to find out.
>
> Please play as you would at home. While you play, say out loud what you're thinking: what you're trying to do,
> what you expect to happen, anything that surprises or annoys you.
>
> I won't be able to answer questions while you play, because I need to see what the game tells you by itself.
> If you're completely stuck for a couple of minutes I'll step in. You can stop at any time."

Rules for yourself:
- Do not explain controls, goals or mechanics. If asked, say: "What would you try?"
- If they are stuck in one place for **two full minutes**, give the smallest possible nudge ("Have a look at the
  top of the screen") and write down that you did, and when.
- If they go quiet, prompt neutrally: "What are you thinking?" Never "Did you notice the...?"
- Note the time (your timer) next to every observation.
- After Duke falls, let them walk on for two or three minutes, then stop the session there.

## Observation sheet (one per player)

**Session** date: ______ facilitator: ______ player code: P__
**Device** type: ______ OS/browser: ______ input: keyboard / gamepad / touch
**Experience** action games: rarely / sometimes / often. Played a belt-scrolling brawler before: yes / no

### A. First two minutes
| What to watch | Target (hypothesis) | Observed | Time |
|---|---|---|---|
| Time from gaining control to first deliberate movement | under 10 s | | |
| Time to first hit on an enemy | under 30 s | | |
| Says or shows they know the goal ("help the woman", "beat these guys") | within 60 s | | |
| Reads the tip panel at the top (eyes or words) | yes | | |
| Tries to hit an enemy from the wrong lane; does the lane ring or tip fix it | fixes itself within 3 tries | | |

### B. Discovering the basics without coaching
Tick only if they did it **on purpose** before Duke. Note what prompted it (tip, accident, prior knowledge).

| Action | Did it? | Prompted by | Time | Notes |
|---|---|---|---|---|
| Three-hit combo | | | | |
| Guard (held, blocked a hit) | | | | |
| Perfect guard (bonus; not expected) | | | | |
| Picked something up and threw it | | | | |
| Entered the diner | | | | |
| Ate (Dot's plate) and noticed the lasting bonus | | | | |
| Visited Benny, took the lesson | | | | |
| Used Shoulder Charge in a real fight afterwards | | | | |
| Broke a blocker's guard (combo finisher, throw, or from behind) | | | | |
| Skipped a tip from the pause menu | | | | |

### C. Getting hit and knocked out
For each knockout, or any hit that visibly surprises them, ask at once: **"What got you there?"**

| Time | Where | Their explanation, in their words | Was it right? | Did they see the tell? |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

Also note: did they choose "try this street again" or the diner after a knockout? Did they change what they did?

### D. Navigation and reading
| What to watch | Observed | Time |
|---|---|---|
| Found Mara's garage without wandering back and forth | | |
| Used the Journal or Map | | |
| Skipped dialogue (which scenes?) | | |
| Read tips fully, skimmed, or ignored them | | |
| Any place they stood still or walked in circles for over 30 s | | |
| Text too small, too fast, or covering the action | | |

### E. Feeling
Mark the moment and what was on screen.

| Time | Frustration / confusion / boredom / enjoyment | What was happening |
|---|---|---|
| | | |
| | | |
| | | |

### F. The neighbourhood after Duke
Do not prompt during play. Note anything they say or do when the neighbours walk into the Chain Lot and the
"Old Quarter" card appears.

| What to watch | Observed |
|---|---|
| Reacted to the neighbours arriving or to the card (words, a laugh, a pause) | |
| Later walked back west and commented on people in the street or the missing Chain Dogs | |

### G. Purchases and numbers (copy from the game after the session)
From **Pause > Help & tips > Playtest notes** and the HUD:

| Item | Value |
|---|---|
| Play time at Duke's defeat (stage "market") | |
| Level, cash on hand | |
| Purchases and what they bought | |
| Knockouts and rooms | |
| Tips completed by doing / skipped | |
| Average FPS and slowest frame (Show FPS readout; note the room) | |
| Any stutter, slowdown or audio problem they mentioned or you saw | |

## Conversation afterwards (10 minutes)
Ask in this order. Write their words, not your summary.

1. "Tell me what the game is about, as if I'd never seen it."
2. "What were you trying to do at the very start? How did you know?"
3. "Was there anything you wanted to do but couldn't work out how?"
4. "When you got hit or knocked out, was it usually clear why? Tell me about one time."
5. "Did anything change in the town while you played?" If yes: "What do you think caused that?"
   (Only if they say nothing changed: "What happened right after the fight with Duke?")
6. "How did fighting feel? Was there anything on screen that helped you, or got in the way?"
7. "Did you hear anything that told you an attack was coming?" (The three attack cues were never checked by ear.)
8. "Did you buy or eat anything? Why that? Did you know what it would do before you chose?"
9. "If you kept playing, what would you do next?"
10. "What one thing would you change?"

## After five sessions
- Tally sections A to C across players. A pattern in three of five is worth acting on; one of five is a note.
- Bring the tallies back to `docs/polish/FOLLOW_UPS.md`: each hypothesis there names the observation that would
  confirm or reject it and the setting or file to change.
- Record what was actually observed separately from the targets above. Do not edit the targets to match.

## What this kit cannot tell you
- Whether the whole campaign holds interest: it only covers the first 25 minutes. A second round on the late
  game (Storage Floor, Kowal) is listed in the follow-ups.
- Performance on devices you did not test. Write down exactly what each session ran on.
