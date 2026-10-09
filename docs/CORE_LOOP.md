# Lowcar — Core Loop Plan

**Draft 2 · October 8, 2026 · Extends `Infinite_Police_Chase_Visual_Style.md` · Vehicle detail in [CAR_BEHAVIOR.md](CAR_BEHAVIOR.md)**

## 1. The fantasy in one line

**Drive as long as you can while the police get bigger, angrier, and more numerous, until the city becomes a pastel demolition derby: cops piling into each other, wrecks exploding, fire everywhere, and you throwing a red muscle car through all of it with ridiculous abilities.**

The current build is a clean *evasion* chase: cops pursue, you slip away, and contact only slows you down. This plan turns it into a *chaos survival* chase. Escaping still matters, but the main pleasure is causing spectacular destruction and staying alive inside it.

### 1.1 Pillars

| Pillar | What it means in play |
| --- | --- |
| **Survive the escalation** | The run never plateaus. Every minute the pursuit gets meaner, until you lose. |
| **Destruction is fuel** | Wrecking cops raises the score, builds the combo, and drops parts that power new abilities. Destruction feeds the next destruction. |
| **Cops are dangerous to each other** | Police AI is aggressive, not careful. They ram, overshoot, and pile up. A clever player makes the police wreck themselves. |
| **Exaggerated, readable physics** | Weird-physics abilities, held Spider-Verse poses, and big impulses. Everything is ridiculous, and everything is still easy to read. |
| **Bright pastel even at its worst** | Explosions and fire use the warm pastel palette in stepped, graphic shapes. Peak chaos still looks like a cartoon, never like grim realism. |
| **Cops win straights; you win corners, air, and impacts** | Police can match your top speed. You beat them by drifting, flying, and outweighing them. You can't simply outrun them. |
| **Aggression rises faster than competence** | Higher heat makes cops attack more often and commit harder, but not much smarter. That's why escalation creates pileups. |

Exactly how every vehicle drives, hits, tumbles, and wrecks is in **[CAR_BEHAVIOR.md](CAR_BEHAVIOR.md)**.

## 2. The loop at three scales

### 2.1 Moment loop (3–8 seconds)

```
See threat → pick a response → perform it → payoff → next threat
```

- **Threat:** a cop lining up a ram, a roadblock ahead, an SUV pinning you, spike strips.
- **Response:** dodge, drift, boost-ram, Ground Punch over it, slam it sideways, bait two cops into each other.
- **Payoff:** a takedown, a pileup, an explosion, a near miss, airtime. The score and combo jump, and a wreck may drop a part.

This is the loop the player feels most of the time. Every ability should produce a different *kind* of payoff.

**The verbs** (details in CAR_BEHAVIOR §3):

| Verb | Input | Role |
| --- | --- | --- |
| Drive | Throttle and steer | Grip driving. Steering softens at high speed. |
| **Drift** | Handbrake tap + steer | Tight turns at speed. Charges boost without slowing you. The swinging tail is a weapon. |
| **Boost → Ram** | Hold, then release | Speed burst. During thrust you outweigh everything up to an SUV. |
| **Ground Punch** | Space or double-click | Launch upward. Has coyote time and an input buffer. |
| **Air Slam** | Punch again in the air | Slam down. On a cop it's a Stomp; on the road it's a shockwave. |
| Air boost | Release boost in the air | A horizontal dash that fixes a bad jump |
| Attachments ×2 | Q / E | Abilities taken from wrecked cops |

The best moments chain verbs together: *drift (charging) → boost out of the corner → ram through → punch over the roadblock → slam onto the cop waiting at the landing.*

### 2.2 Wave loop (30–90 seconds)

```
Heat rises → new unit type arrives (telegraphed) → surge → you thin the pack → brief breather → heat rises higher
```

Heat (section 3) drives the waves. The key rhythm is **surge and breather**. After a big multi-takedown, the pursuit briefly regroups (a few seconds with fewer cops nearby, and sirens fading behind you), then reinforcements arrive harder. Without breathers, constant max pressure turns into noise.

### 2.3 Run loop (one life, 2–15 minutes)

```
Start clean → collect parts and abilities → escalate to absurd → wreck or get busted → results → instant restart
```

The run ends one of two ways:

- **WRECKED:** the car's integrity reaches zero, or it hits a lethal high-speed impact.
- **BUSTED:** the arrest meter fills (this already exists and is kept).

On the results screen, distance, time, takedowns, best combo, peak heat, and the Mayhem score each get a stat line. Then one button starts a new run.

### 2.4 Meta loop (later, optional)

Unlockable starting attachments, car paint variants, and daily seeds. These are out of scope for the first chaos pass. Get the run fun first.

## 3. Heat: the escalation engine

### 3.1 Replace the timer with Heat

Today, `ChaseDirector` raises the tier every 30 seconds (`seconds_per_tier`). Replace that with a **Heat** value that rises from both time *and* the player's mayhem:

| Source | Heat gain (starting values) |
| --- | --- |
| Time survived | +1 per second |
| Cop takedown | +12 |
| Cop pileup (cop-on-cop) | +8 per car involved |
| Explosion | +6 |
| Smashing a roadblock | +15 |
| Destroying a helicopter or heavy unit | +30 |

Heat never decreases during a run. Thresholds unlock **heat levels**. Playing wild escalates faster, which is a fair trade because it also scores more and drops more parts. A cautious player escalates slowly but scores little.

### 3.2 Heat levels

Each level *adds* a unit type or tactic. Earlier units stay in the mix.

| Level | Heat | New threat | What it changes |
| --- | --- | --- | --- |
| 1 | 0 | **Patrol sedans** (2–3) | Learn driving, ramming, and pins. They are fragile and easy takedowns. |
| 2 | 60 | **Interceptors** | Fast, low, and wide. They catch you on straights and attempt PIT maneuvers. |
| 3 | 150 | **Roadblocks + spike strips** | The director places formations at upcoming intersections. Spikes cut grip for a few seconds. |
| 4 | 280 | **Armored SUVs** | Heavy rammers. They survive several hits and shove you into walls. |
| 5 | 450 | **Helicopter** | A spotlight tracks you and calls in cops from ahead. It drops flash charges. You can destroy it by launching into it. |
| 6 | 650 | **SWAT carriers** | They deploy barrier walls and drop spike mats across lanes. |
| 7 | 900 | **Police launchers** | Cops with their own Ground Punch. They jump onto you, or over your blockades. ("The bureaucracy has acquired a trampoline budget.") |
| 8 | 1200 | **Tank / APC** | Nearly indestructible. It crushes cop cars in its path and fires slow, telegraphed shells that cause huge explosions. |
| 9+ | +400 each | **Absurd** | Counts and aggression keep scaling. Mixed formations, multiple helicopters, and simultaneous roadblocks. The run must end eventually. |

The population cap rises with level, for example 3 → 14 active units. Wrecks don't count toward it. Keep a hard performance ceiling (section 8).

### 3.3 Arrival is always telegraphed

Each new unit type gets a short HUD silhouette pop-in ("⚠ INTERCEPTORS"), a siren-tone change, and a first appearance in the camera's view. The player never dies to something they haven't seen yet.

### 3.4 The encounter director: pacing, not just numbers

Heat decides *what* can appear. An **encounter director** decides *when*, based on how intense things currently are for the player.

**Intensity** rises with nearby cops, damage taken in the last 5 s, low integrity, and being boxed in. It falls during clean driving.

The director cycles through three phases:

| Phase | Behavior |
| --- | --- |
| **Build** | Spawn units toward the heat target and hand out attack tokens (CAR_BEHAVIOR §5.6) |
| **Peak** | Fire one set piece from the encounter deck |
| **Relax** | Starts after intensity peaks, or right after a pileup of 3+. For 3–6 s there are no new spawns, attack tokens are withheld, and surviving cops "search" (sirens fade, they drive wider). This is where the player breathes, picks up parts, and lines up the next move. |

**Encounter deck** (unlocked by heat level; the director never plays the same one twice in a row, and plays at most one set piece every 20 s):
- Roadblock at the next intersection
- SUV ambush from a side street
- Spike line across an avenue
- Interceptor pack from behind
- Helicopter sweep
- SWAT rolling roadblock
- Police-launcher rain
- Tank crossing

The director also *reads the city*: roadblocks go where streets are narrow, interceptor packs come on long avenues, and ambushes come where side streets meet the road.

## 4. Chaos systems

### 4.1 Police damage and wreck states

Police currently can't be destroyed. Each unit gets **health** and visible damage states:

| State | Trigger | Look (stepped, ~12 poses/sec) |
| --- | --- | --- |
| Intact | — | Clean navy and white |
| Dented | <70% HP | Body panels pop to bent poses, the lightbar tilts |
| Smoking | <35% HP | Chunky pale-grey smoke puffs and a limp handling wobble |
| **Wrecked** | 0 HP | Converts to a physics wreck (4.2). The AI is gone and the lights die with a last flicker. |
| **Burning** | Wrecked + more damage, or caught in fire | Pastel flame clumps on the wreck. A fuse timer runs. |
| **Exploded** | Fuse runs out, or a big hit lands on a burning wreck | Explosion (4.4) and a charred shell left behind |

Unit toughness, starting values:

| Unit | Health |
| --- | --- |
| Patrol | 40 |
| Interceptor | 50 |
| SUV | 140 |
| SWAT carrier | 200 |
| Helicopter | 60 |
| Tank | Destructible only by explosions and heavy stomps |

### 4.2 Wrecks are physics objects

On wreck, swap the `PoliceVehicle` (an AI-driven `ArcadeVehicle`) for a pooled **`RigidBody3D` wreck** that inherits its velocity, plus a spin impulse and an upward kick. Wrecks then:

- tumble, roll, and slide with exaggerated impulses (about 1.5–3× realistic)
- become **obstacles and weapons**: a sliding wreck can take out the cop behind it
- linger about 15 seconds, then fade or sink. The oldest are recycled past the cap.

This one swap gives you most of the "cops crashing into each other" spectacle for free.

### 4.3 Cop-on-cop collisions

This is where the comedy comes from:

- **Damage on any vehicle-vs-vehicle contact**, scaled by relative speed. Police take damage from hitting each other, walls, wrecks, and their own roadblocks.
- **Aggressive AI on purpose.** Higher heat makes cops commit harder to ram lines and predict worse around jumps. They brake late, so they overshoot when you dodge and plow into each other. Tune the AI to be *threatening but crashable*.
- **Bait plays.** A sudden handbrake turn makes two pursuers converge. A Ground Punch over a cop makes the one behind it rear-end it.
- **Pileup bonus:** two or more cops wrecked in the same incident within one second is a "PILEUP x3!" with big score and heat.

Current code to change: `PoliceVehicle._drive` slows down and steers around obstructions (it slows when the 7 m forward ray hits something). Keep that for walls only. Against the player and other cops at high heat, they should commit and collide.

### 4.4 Explosions

An explosion is an `Area3D` burst that does three things:

1. **Impulse:** it shoves every rigid body and vehicle in its radius away and upward. This includes the player, so a nearby blast can throw you somewhere useful or somewhere terrible.
2. **Damage** with falloff. Police caught inside can wreck, and burning wrecks nearby **chain-explode**.
3. **Visual:** a stepped graphic burst. It holds a big starburst pose, then breaks into chunky puffs, with a cream core, a coral and amber ring, and dusty lavender smoke. The camera gets a punch impulse scaled by distance (the comfort setting reduces it).

Chain reactions are the peak spectacle: a burning roadblock, a stomp, then five cars going up in sequence.

### 4.5 Fire

- Burning wrecks and exploded fuel leave **fire patches** on the road for about 6 seconds.
- Fire damages cops that drive through it (about 15 HP per second) and lightly damages the player (they can boost through).
- Cops can be **baited through fire**, and the car can drag fire behind it if it drives over a patch while boosting. That's an option for later.
- Look: stepped, low-poly flame cones in the warm palette (cream tip, amber body, coral base), cycling 3–4 poses at about 12 fps. Not realistic fire.

### 4.6 Debris and the environment

Breakable props should be added: lamp posts, bins, cones, café tables, awnings, fences, roadblock barriers. They're cheap `RigidBody3D` pieces that spawn on impact. Buildings stay solid and lethal at speed. That keeps the street readable and makes "don't hit the wall" a real skill.

## 5. The player car

The full spec is in [CAR_BEHAVIOR.md](CAR_BEHAVIOR.md). The summary:

### 5.1 Integrity instead of instant death

Add **integrity** (100), shown *on the car*: dents, then smoke, then fire under the hood at low integrity, with the bumper hanging. A small meter goes bottom-left next to speed.

| Hit | Integrity damage |
| --- | --- |
| Cop contact | Scaled by closing speed, the other car's mass, and the hit type. The hero takes about 0.35× what a cop would. |
| Wall scrape (< 30°) | Small. You slide along at 85–90% speed. |
| Wall bounce | Medium, plus a 0.25 s stagger |
| Wall head-on, normal speed ≥ 24 m/s | **Instantly WRECKED.** Walls stay deadly. |
| Explosion | Up to 30 at the center |
| Fire | 5 per second |

**Repair:** some wrecks drop a wrench pickup worth +25.

### 5.2 Offense is mass and geometry

Every vehicle has a cartoon mass. The red car (1.6) outweighs patrols (1.0) and interceptors (0.85), and loses to SUVs (2.4) unless boosting (×3). *Where* you hit matters:

| Hit | Result |
| --- | --- |
| **T-bone** | Rolls them. The best normal takedown. |
| **PIT** | They spin out into whatever's nearby |
| **Sideswipe** | Shoves them into walls, wrecks, or fire |
| **Tail whip** | Your drifting rear knocks them aside |
| **Ram** (boost) | Smash straight through and keep about 90% speed |
| **Stomp** (Air Slam) | Crushes them flat, then they explode |
| **Near miss** | Within about 1.5 m at speed: score and combo, no damage |

Big hits get **hit-stop** (30–100 ms) for crunch. Knocked cops become tumbling physics toys that bounce, shed their lightbars, and land on other cops.

## 6. Abilities: crazy escapes

### 6.1 Structure

- **Boost** is always available. It already exists, and it gains the boost-ram rule.
- **Ground Punch** is the starting attachment. It already exists.
- **Two attachment slots** (Q and E, or the shoulder buttons). New attachments come from **wrecked cops dropping parts**. The visual style doc (§9.9) already anticipates "stealing" police equipment. A wrecked unit flings its part out with a pastel glint, you drive through it, and it snaps onto the car with one mechanical pop.
- Picking up a part you already have adds charges or upgrades it.

### 6.2 Attachment roster

| Attachment | Dropped by | What it does | Chaos angle |
| --- | --- | --- | --- |
| **Ground Punch** (have) | Start | Slams the road and launches the car. Press again in the air to **Air Slam**. | Stomps, clearing roadblocks, dodging spikes |
| **Shockwave Landing** | Upgrade to Ground Punch | Every hard landing releases the Air Slam shockwave, and the Slam's radius doubles | Lands in a crowd and scatters it |
| **Ram Plow** | Armored SUV | A front plow. Boost-ram takes down SUVs, and normal rams count as boost rams for 8 s | Plows through roadblocks |
| **Side Slammer** | Interceptor | A lateral piston kicks the car sideways *and* punches whatever is beside it | Slam cops into walls; dodge PITs |
| **Spike Dropper** | SWAT carrier | Drops a spike mat behind you; cops spin out | Sets up pileups behind you |
| **Oil Slick** | Patrol | A slick that sends cops sliding wildly; combined with fire it becomes a flame trail | Chain-reaction setups |
| **EMP Pulse** | Helicopter | Kills the engines and lights of nearby cops for 3 s; the helicopter drops | Escape tool and breather |
| **Grapple** (later) | Rare / heat 6+ | Hooks a building corner and swings the car around it; or hooks a cop and slingshots it | Peak "crazy escape" moment |

Each attachment follows the style doc's grammar: one chunky mechanism, one accent color, a readable pose. Readiness shows in the mechanism's shape, not just a glow.

## 7. Score: Mayhem and combo

- **Mayhem score** = takedowns, pileups, explosions, stomps, near misses, airtime, and roadblock smashes.
- **Combo multiplier** (x1 → x10) builds while chaos keeps happening, and decays after about 3 s of calm. It encourages playing close to danger instead of just fleeing.
- **Callouts:** short stepped text pops in the HUD margin, such as "STOMP!", "PILEUP x4", "CHAIN x3", "THREADED THE NEEDLE". They follow the style doc's UI animation (snap and overshoot once) and stay out of the driving corridor.
- The run summary shows distance, time, Mayhem, best combo, peak heat level, and takedowns by type.

## 8. Readable chaos: the visual rules

The style doc asks for restraint, while this plan asks for mayhem. Here is how they fit together:

1. **The player car is always readable.** Effects near the car fade in its screen-space zone, and the car keeps its scarlet silhouette even inside an explosion.
2. **Chaos budget.** Cap concurrent big effects at about 4 explosions and about 10 fire patches; wrecks and debris have caps too. Merge or retire the oldest effects instead of stacking them.
3. **Everything is stepped.** Explosions, fire, smoke, and wreck tumbles use about 12 fps held poses, the same rhythm as the car. Chaos then looks *authored*, not like a particle soup. Physics stays smooth, and only the look is stepped.
4. **Pastel destruction palette.** Fire and explosions use cream (#F7F1E6), amber (#E8AD43), coral (#F08A6E), and lavender-grey smoke (#B9B3C9). There's no black smoke or gore. Charred wrecks go dusty slate, not black.
5. **Pastel world, saturated action: if it's saturated, it matters.** The city is lifted to pastel. Only gameplay things are saturated: the scarlet car, police lights, amber attachments and pickups, fire cores, and telegraph circles. Proposed swatches are in CAR_BEHAVIOR §9.
6. **Nobody gets hurt.** Cars are toys. Wrecked cops pop out as tiny figures, shake a fist, and stomp off. Burning wrecks are always empty.
7. **Smears on impacts.** Big hits get the same smear and held-pose treatment as the launcher. A rammed cop holds a squashed pose for 2–3 frames, then flies.
8. **In the zone.** The car animates on twos (12 pps) normally and on ones (24 pps) during a hot combo. It literally looks more confident when you're playing well.
9. **Camera:** impacts punch the camera, explosions push it, and big hits get hit-stop (CAR_BEHAVIOR §4.7). Every shake and hit-stop can be reduced in settings.

Performance ceiling for the first pass: 14 active police, 12 wrecks, 4 explosions, 10 fire patches, 40 debris bodies. Pool everything.

## 9. Pacing curve: what a good run feels like

| Time | Feel |
| --- | --- |
| 0:00–0:45 | Cruise and learn. A couple of patrols. The first ram and the first takedown. |
| 0:45–2:00 | Interceptors arrive. The first pileup. The first part drop and new attachment. Combos start. |
| 2:00–4:00 | Roadblocks, spikes, and SUVs. Real decisions at intersections. The first explosion chain. |
| 4:00–7:00 | The helicopter, SWAT, and cops jumping. The screen is busy, fire is everywhere, and you're juggling 2 attachments plus boost. |
| 7:00+ | Absurd. Tanks crushing their own cops. Survival is about reading the chaos, and death is inevitable and spectacular. |

A good-but-not-expert player should average 3–5 minutes. Tune heat gain and health so this holds.

## 10. Build order

Each milestone should leave the game playable. Keep `tools/verify.sh` green throughout.

### M1: Impacts and cops can die (the biggest single fun jump)
- `ImpactSolver`: mass classes, winner/loser, hit types, knockback, damage, and hit-stop (CAR_BEHAVIOR §4). Remove the flat `forward_speed *= 0.35` contact penalty.
- `health` and damage states on `PoliceVehicle`. A pooled `TumbleProxy` (`RigidBody3D`) for knocked and wrecked cops; upright and alive returns to driving, upside down means turtled.
- Boost becomes Ram (×3 mass).
- **Check:** a T-bone wrecks a patrol, a Ram keeps about 90% speed, and two cops colliding both take damage.

### M2: Driving feel
- Speed-sensitive steering, the drift state (charging without slowdown, tail whip), and the angle-based wall response.
- Apex hang, coyote time, input buffer, Air Slam and Stomp, and auto-right on landing.
- **Check:** a 20° scrape at 32 m/s survives; drifting out-turns grip driving at speed.

### M3: Police brain
- `PoliceBrain` state machine: pursue → position → telegraph pose → commit → recover. Attack tokens.
- Aggression-vs-competence scaling, rookies and veterans, and the physical box-in capture.
- **Check:** baiting a committed cop into another produces a pileup.

### M4: Explosions and fire
- `Explosion` scene: impulse, damage falloff, chain-reaction to burning wrecks, and a stepped pastel visual.
- Overkill-based burning, fuse timer, `FirePatch`.
- Camera punch.

### M5: The player can take damage
- Integrity, visible damage states on the red car, the WRECKED ending, and wrench drops.
- Stagger and hero armor.

### M6: Heat, director, and new units
- `HeatSystem` replaces the timer-based tier in `ChaseDirector`. Add the encounter director with build, peak, and relax phases.
- Interceptor, then roadblocks and spikes, then the armored SUV ambush. Each with a HUD arrival telegraph.

### M7: Part drops and attachment slots
- Two attachment slots and drop/pickup with the snap-on animation.
- Side Slammer, Ram Plow, and Spike Dropper first; Oil Slick, EMP, and Shockwave Landing next.

### M8: Mayhem score and combo
- Score, multiplier, callouts, "in the zone" animation on ones, and new results-screen stats.

### M9: Top-end units
- Helicopter, SWAT carrier, police launchers, tank. "Absurd" scaling past level 9.

### M10: The street as a weapon and chaos polish
- Awning trampolines, hydrant geysers, falling lamp posts, parked cars, gas stations (CAR_BEHAVIOR §7).
- Pastel palette pass, the effect budget and pooling pass, comfort settings, and sound (crunches, explosions, siren layering).

## 11. Decisions for you

1. **Integrity vs one-hit walls:** Is the integrity bar plus "fast wall hit is still instant death" right? Or should the car be fully one-hit like now?
2. **Heat from mayhem:** Should destruction speed up escalation (risk/reward), or should escalation be time-only?
3. **Attachment slots:** two slots fed by cop drops, or a fixed loadout picked before the run?
4. **Civilians:** add civilian traffic as extra chaos? The style doc mentions it, but nothing in the city uses it yet.
5. **Tone ceiling:** do tanks and police jumping-cars fit, or should it stay "street cops only"?
6. **Pastel shift:** lighten the whole palette toward pastel (proposed in CAR_BEHAVIOR §9), or keep the style doc's warm-matte values and only make the chaos effects pastel?
7. **Cop speed:** are you OK with interceptors out-running you on straights, so you *have* to fight and drift instead of just fleeing?
8. **Air Slam:** should it be on the same button as Ground Punch (press twice), or a separate input?
