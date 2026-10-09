# Lowcar — How Cars Behave

**Draft 1 · October 8, 2026 · Companion to [CORE_LOOP.md](CORE_LOOP.md) and `Infinite_Police_Chase_Visual_Style.md`**

This is the physical personality of every vehicle in Lowcar: how the red car drives, drifts, flies, lands, and hits things; how police drive, attack, miss, and crash; and how a car that's been hit turns into a tumbling cartoon toy. All numbers are starting proposals for tuning in the running game.

## 0. What the current code does that fights the vision

These are the specific behaviors in today's build that block "smash through cops in a pastel demolition derby". Each one is addressed below.

| Today (file) | Effect in play | Fix (section) |
| --- | --- | --- |
| Any contact above 1 m/s multiplies speed by 0.35 (`arcade_vehicle.gd`) | Ramming a cop is the same as braking. The player learns to avoid contact. | Mass-based impact solver: winner keeps most of its speed (§4) |
| Vehicles are `CharacterBody3D` and don't push each other | Cops can't be knocked, spun, flipped, or sent into each other | Knockback velocity + tumble proxy (§4, §7) |
| Wall death at 12 m/s *normal* speed | At cruise (32 m/s), a 22° glancing scrape ends the run | Angle-based wall response; lethal only near head-on (§3.7) |
| Full steering rate at any speed above 12 m/s | The car corners as tightly at 115 km/h as at 40, so drifting is never needed | Speed-sensitive steering plus a real drift state (§3.2–3.3) |
| Patrols: 30 + 2.4 m/s per tier, steering 3.0 vs player 1.65, grip 13 vs 9 | From tier 2, cops are faster *and* corner better. The player is out-driven everywhere. | "Cops win straights, you win corners, air, and impacts" (§5.1) |
| Handbrake is just low grip | Sliding has no control, angle, or reward | Drift state that charges boost and swings the tail as a weapon (§3.3) |
| Capture: any cop within 7.5 m while you're under 7 m/s | Getting "arrested" can feel unphysical in a crowd | Capture needs a real box-in (§5.8) |

## 1. Behavior principles

1. **The hero is a brick with a rocket.** The red muscle car is heavy, planted, and wins most collisions. It feels obedient at the wheel and overcommitted in the air.
2. **Cops win straights; you win corners, air, and impacts.** Police can match or beat your top speed as heat rises. You beat them with drifting, abilities, and mass. You can't simply outrun them, so you have to outplay and outsmash them.
3. **Everything you hit becomes a toy.** A struck car stops being a driver and becomes a bouncing, spinning cartoon object with exaggerated impulses. It's a hazard for whoever is behind it.
4. **Aggression rises faster than competence.** As heat climbs, cops attack more often and commit harder, but their judgment improves only a little. Escalation makes them more dangerous *and* more self-destructive. That's where the pileups come from.
5. **The pose is the telegraph.** Every stepped Spider-Verse anticipation pose is also a gameplay warning. A cop loading its suspension toward you *is* the attack wind-up. The style and the readability are the same system.
6. **The player is never cheated.** The car never lands on its roof, never gets stuck, and never dies to something it couldn't see. Chaos is unfair to the cops and fair to the player.

## 2. Four simulation layers

```
┌───────────────────────────────────────────────────────────────┐
│ 4. PRESENTATION   stepped 12/24 pps poses, smears, effects    │  looks only
├───────────────────────────────────────────────────────────────┤
│ 3. TUMBLE PROXY   RigidBody3D for knocked / wrecked cars      │  physics toy
├───────────────────────────────────────────────────────────────┤
│ 2. IMPACT         mass classes, hit types, knockback, damage  │  resolves contact
├───────────────────────────────────────────────────────────────┤
│ 1. DRIVING        arcade CharacterBody3D, driver commands     │  authoritative control
└───────────────────────────────────────────────────────────────┘
```

- **Driving** stays as it is now: crisp, readable, and authoritative for the player. A driven car's velocity is `drive_velocity + knockback_velocity`.
- **Impact** runs when two bodies touch. It decides who wins, applies knockback, damage, and stagger, and emits one `impact` event that effects, score, camera, and audio all listen to.
- **Tumble proxy:** when a cop gets hit hard enough (knockback > 14 m/s, a vertical pop > 6 m/s, or HP ≤ 0), its driver is switched off and a pooled `RigidBody3D` takes over with the same mesh. If it comes to rest upright and alive, it goes back to driving. If it lands on its roof or has no HP left, it's a wreck.
- **Presentation** never moves anything. Orientation and deformation are stepped; position is always smooth. That rule already holds for the car, and it extends to every vehicle and wreck.

The player car never uses a tumble proxy. It keeps arcade control and gets knockback plus stagger only (§3.8).

## 3. The red car

### 3.1 Feel target

*Heavy, planted, obedient, overcommitted.* At the wheel it does exactly what you ask. When something hits it, the something usually loses. In the air it hangs, poses, and drops like a dumbbell.

### 3.2 Grip driving

Steering rate scales with speed so that high-speed turning *needs* a drift:

| Speed | Steering rate (fraction of `steering_radians_per_second`) |
| --- | --- |
| 0–12 m/s | Ramps 0 → 1.0 (current behavior) |
| 12–18 m/s | 1.0 |
| 18–32 m/s | Eases 1.0 → 0.6 |
| Boost thrust | 0.45 |
| Airborne | 0.5 (yaw only) |

Weight transfer is already in the animation pack: nose lift, dip, and loaded outside tires. Keep it. Add one *gameplay* use: braking hard right before a turn makes the next drift entry faster (brake-tap entry, below).

### 3.3 Drift: the second core verb

Drift becomes a real state with an angle, a reward, and an attack.

**Entry:** above 14 m/s, either tap the handbrake while steering, or brake briefly then steer hard. Holding the handbrake without steering is still a straight-line slide or brake.

**While drifting:**
- The body yaws away from the travel direction. Target slip angle = 20° + 25° × |steer|. Counter-steer narrows it toward 10°.
- Yaw rate rises to about 2.4 rad/s, so the car turns *tighter* at speed than grip driving allows. Cornering is how you beat cops.
- Speed bleeds slowly (about 2 m/s²). Throttle holds the drift.
- **Drift charges boost without the slowdown.** Today, charging boost cuts speed to 72% → 36%. Charging during a drift skips that penalty. This is the key synergy: drift around a corner while charging, then release out of it as a ram.
- **Tail whip:** the swinging rear quarters become an attacking surface. A cop clipped by your tail during a drift takes a "whip" hit (§4.4).

**Exit:** straighten or counter-steer with throttle. The car snaps back over two held poses. Drifts longer than 0.8 s give an exit kick of +3 m/s.

**Look:** a held diagonal pose, a cream swish trailing the rear axle, and grouped tire puffs. These are mostly in the visual style doc already.

### 3.4 Boost becomes Ram

Boost charge and release stay as built. During thrust, the car enters **Ram**:

- Effective mass ×3 (§4.2). The front 120° cone *dominates* everything up to an armored SUV.
- Patrol cars and interceptors hit by the nose during Ram are instantly wrecked and launched.
- Walls are still walls. A boosted head-on into a building is the most spectacular way to lose.
- **Air boost:** releasing boost while airborne gives a horizontal dash and cancels downward speed for 0.15 s (a held "hover" pose). It's for fixing a bad jump, or crossing a gap over a roadblock.

### 3.5 Ground Punch, air, and the Slam

Current Ground Punch: 24 m/s upward with gravity 25 m/s², so an apex of about 11.5 m (3–4 stories) and about 1.9 s of air. Keep that, and add:

- **Apex hang:** while |vertical speed| < 3 m/s, gravity ×0.55. This creates the suspended "breath" pose from the style doc for about a quarter second. While falling, gravity ×1.15, so the drop feels heavy.
- **Coyote time:** you can still punch for 0.15 s after leaving the ground, for example off a curb or a ramp.
- **Input buffer:** a punch pressed up to 0.15 s before touching down fires on landing. That makes bunny-hop chains possible.
- **Air Slam (new):** press punch again in the air. The piston swings to point down, the car freezes for 80 ms in a held wind-up pose, then slams down at 45 m/s.
  - Landing it on a cop is a **Stomp**: the cop is crushed flat in a squash pose and explodes a beat later.
  - Landing it on the road sends a shockwave with a 6 m radius: 35 damage at the center, knockback 12 m/s outward and 6 m/s up.
  - It costs the punch cooldown.
  - The full verb chain is: *punch up, read the street, slam onto the cop blocking your landing.*

### 3.6 Landing

- Within 35° of level, the landing is clean: the existing graded squash, plus a short grip reduction on hard landings.
- Nose-first or very tilted: one bounce plus a 0.3 s stumble with reduced steering. It never flips.
- **Auto-right:** in the last 0.4 s before ground contact, the car twists toward level in two held poses, like a cat. The player never lands on the roof.
- **Stick the landing:** throttle held within 0.2 s of a clean landing gives +2 m/s and a small score callout.

### 3.7 Walls and buildings

Use the angle and the *normal* speed (how fast you're going straight into the wall):

| Contact | Condition | Result |
| --- | --- | --- |
| Scrape | Angle < 30° | Slide along the wall at 85–90% speed. Sparks streak along the contact. Integrity −(normal × 0.5). |
| Bounce | 30–60°, or normal speed 10–24 m/s | Deflect off the wall, speed ×0.5, 0.25 s stagger, integrity −(normal × 1.6) |
| Lethal | Normal speed ≥ 24 m/s (≈86 km/h straight in) | WRECKED, regardless of integrity |

Scraping walls at full speed becomes *survivable and stylish*, and plowing straight into a building stays the classic death. If you prefer the current one-hit rule, keep the same angle logic and drop integrity: scrapes become free, bounces stagger, and lethal still kills.

### 3.8 Stagger and hero armor

When the player loses a collision (§4.3):
- Knockback is capped at 18 m/s.
- **Stagger** lasts 0.3–0.6 s: steering ×0.4, a held hit pose, and the body yawing with the impact.
- **Hero armor:** 0.8 s of immunity to further stagger after one ends, so three cops can't juggle you to death.
- Abilities still fire during stagger. A Ground Punch out of a box-in is always an escape.

### 3.9 Never-cheated rules

- The player never ends upside down.
- If the car is stuck (no progress for 1.2 s while pressing throttle), it gets a free shove out.
- No run ends from an off-screen cause. Lethal hits must be on camera for at least 0.3 s first.
- Telegraphs are never shorter than 0.3 s.
- Explosions push the player but never flip the car.

## 4. Mass, momentum, and impacts

This section is the heart of smashing.

### 4.1 Mass classes (cartoon mass, not real mass)

| Vehicle | Mass | Health | Notes |
| --- | --- | --- | --- |
| **Red muscle car** | 1.6 | Integrity 100 | Heavier than any car its size, by design |
| Patrol sedan | 1.0 | 40 | Bowling pin |
| Interceptor | 0.85 | 50 | Fast and light. It flies far when hit. |
| Police launcher | 1.4 | 60 | Sturdy legs |
| Armored SUV | 2.4 | 140 | Beats you head-on unless you boost |
| SWAT carrier | 3.5 | 200 | Rolling wall |
| Tank / APC | 12 | ∞* | *Only explosions and Stomps hurt it |
| Civilian car / van / bus | 0.9 / 1.3 / 4.0 | 30 / 45 / 150 | Optional traffic |
| Wreck (any) | 0.8 | — | Slides far, low friction |
| Street props | 0.05–0.3 | — | Bins, cones, café tables, signs |

### 4.2 Effective mass modifiers

| Condition | Multiplier |
| --- | --- |
| Ram (boost thrust), front cone | ×3 |
| Ram Plow attachment, front | ×2 (×4 combined with Ram) |
| Stomp / Air Slam, from above | ×4 |
| Tail whip (rear quarter during drift) | ×1.3 |
| Staggered or spinning | ×0.7 |
| Airborne (not slamming) | ×0.8 |
| Police committed to an attack | ×1.2 |

### 4.3 Who wins a hit

The mass ratio is r = m_eff(A) / m_eff(B), and the closing speed is how fast they approach each other along the contact normal.

| Ratio | Outcome |
| --- | --- |
| r ≥ 1.25 | **A wins.** B gets knockback = min(closing × m_A/(m_A+m_B) × 1.8, cap). A loses speed of closing × m_B/(m_A+m_B) × 0.6. |
| 0.8 < r < 1.25 | **Even hit.** Both get half knockback and both stagger. This is how cop-on-cop pileups happen. |
| r ≤ 0.8 | **B wins.** Same as the first row with A and B swapped. |

Knockback caps are 18 m/s for the player and 40 m/s for everything else. A cop's knockback gets an upward pop of 20–35% of its magnitude and spin from how off-center the hit was.

**Worked examples**

| Situation | Result |
| --- | --- |
| You (1.6) T-bone a stopped patrol at 32 m/s | You win with r = 1.6. The patrol is knocked about 35 m/s sideways (tumble). You keep about 77% speed. |
| Same hit during Ram (4.8) | The patrol is launched. You keep about 90% speed. **This is "smashing through".** |
| Head-on into an SUV (2.4) without boost | r = 0.67, so the SUV wins. You're knocked back 18 m/s (capped) and staggered. Lesson: boost first. |
| Two patrols collide | r = 1.0, an even hit. Both bounce and stagger, and at speed both tumble. |

### 4.4 Hit types by geometry

Where you hit them matters as much as how hard.

| Hit type | Geometry | Damage × | Special effect |
| --- | --- | --- | --- |
| **Head-on** | Front to front | 1.0 | Both take full damage. Risky. |
| **T-bone** | Your front into their side | 1.5 | Rolls them over. Best normal takedown. |
| **Rear-end** | Front into their back | 1.0 | A shove. Low closing speed means small damage, unless you're in Ram. |
| **PIT** | Your front corner into their rear quarter with lateral push | 0.4 | They spin out for 1.2 s and drift into whatever's nearby. Low damage, high chaos. |
| **Sideswipe** | Side to side | 0.6 | A strong lateral shove. Push them into walls, wrecks, or fire for environmental damage. |
| **Tail whip** | Your rear quarter during a drift | 1.2 | Knocks them sideways out of the drift arc |
| **Stomp** | From above with Air Slam | 2.0 | Crush pose, then a delayed explosion |

### 4.5 Damage

```
damage_to_X = closing_speed × m_eff(other) × hit_type_multiplier × K_X
K_cop = 1.2      K_player = 0.35   (the hero is armored)
```

| Example | Damage |
| --- | --- |
| Normal T-bone at 32 m/s on a patrol | 32 × 1.6 × 1.5 × 1.2 = 92 → wrecked (HP 40), with 52 left over (§6.1) |
| Rear-ending a patrol going 28 while you go 32 | 4 × 1.6 × 1.0 × 1.2 = 8 → just a nudge |
| The same rear-end in Ram at 50 m/s | 22 × 4.8 × 1.2 = 127 → wrecked |
| Head-on with a patrol, both at 30 m/s | Patrol takes 115 (wrecked). You take 60 × 1.0 × 0.35 = 21. |
| An SUV T-bones you at 30 m/s | 30 × 2.4 × 1.5 × 0.35 = 38 integrity |

Walls damage cops by normal × 2.5, so a sideswipe into a wall at 10 m/s costs a cop 25. Two wall slams wreck a patrol.

### 4.6 Cop-on-cop is the same physics

There are no special rules. Police use the same solver, the same damage, and full friendly fire. The only difference is behavioral: a committed cop doesn't brake for other cops (§5.4). That alone produces most pileups.

### 4.7 Hit-stop: the crunch

A brief time freeze on impact makes hits feel heavy. It is real time, with the presentation holding its pose:

| Impact | Hit-stop |
| --- | --- |
| Light (no stagger) | 0 |
| Medium (stagger) | 30 ms |
| Heavy (tumble) | 60 ms |
| Wreck / T-bone takedown | 80 ms |
| Stomp, or a chain explosion of 3+ | 100 ms |

Allow at most one hit-stop per 250 ms, so a 6-car pileup reads as one crunch and not a stutter. A comfort setting can turn it off.

### 4.8 How a knocked car moves

This is the comedy, as a stepped sequence:

1. **Impact frame:** 2 held frames on *ones* (24 pps) of the crumple pose. The lightbar snaps crooked.
2. **Smear:** one frame of directional stretch along the knockback.
3. **Tumble:** the rigid body flies with smooth position, while *rotation is shown at 12 pps*. That gives the jerky, graphic spin. Parts pop off as debris in a fixed order: lightbar first (iconic), then bumper, hubcap, and door.
4. **Toy bounce:** the first ground contact has restitution 0.5, so it bounces like a rubber toy. Later contacts use 0.15.
5. **Settle:** if it ends upright with HP left, it gets 0.6 s of a dazed wobble pose, then drives again. Upside down means **turtled**: wheels spin in the air and it's out (counts as a takedown).

## 5. Police behavior

### 5.1 How cops drive

| | Player | Patrol | Interceptor | SUV |
| --- | --- | --- | --- | --- |
| Top speed | 32 cruise, 38–64 boost | 28 + 1.2/level (cap 36) | 33 + 1.2/level (cap 44) | 27, with a 36 ram burst |
| Steering (rad/s) | 1.65, high-speed falloff to 0.6 | 3.0 → **2.2**, falloff to 0.55 | 2.0 | 1.6 |
| Corners | Drift | Brake hard (already built) | Brake hard | Brake very hard |
| Air | Full verb set | Only when knocked | Only when knocked | Only when knocked |

Interceptors catch you on long straights by mid-game. Nobody corners like you. Long boulevards are dangerous; twisty neighborhoods are your turf. That gives districts a gameplay identity.

**Rubber band (light):** cops more than 70 m behind get +20% speed until they're within 40 m. Nothing slows cops near you; their mistakes do that job.

### 5.2 State machine

```
PURSUE ──► POSITION ──► TELEGRAPH ──► COMMIT ──► RECOVER ──► PURSUE
                                         │
            any hard hit ────────────────┼──► STAGGER (spin, 0.5–1.5 s) ──► PURSUE
                                         └──► TUMBLE (rigid proxy) ──► PURSUE / WRECK / TURTLED
WRECK ──► BURNING ──► EXPLODED
```

The current `PoliceVehicle._drive` becomes the *executor* of whatever the state wants: a route, an aim line, or a brake. A separate brain picks the state.

### 5.3 Telegraph = pose

Every attack has a readable wind-up made of a stepped pose, a light cue, and a sound or ground cue:

| Attack | Wind-up pose | Extra cue | Base telegraph |
| --- | --- | --- | --- |
| Side bump / PIT | Body leans toward you; outside wheels load | Headlight double-flash | 0.45 s |
| SUV ram | Squat low, nose dips, held 3 frames | Engine roar, siren drops pitch | 0.6 s |
| Brake-check (interceptor ahead) | Brake lights flare, nose dips | Tire chirp | 0.4 s |
| Police launcher hop | Deep crouch | **Pastel landing circle on the road** | 0.8 s |
| Tank shell | Turret swings and holds | **Circle on the impact point, closing in** | 1.2 s |
| SWAT spike deploy | Rear doors swing open | Spike mat visibly sliding out | 0.6 s |

Telegraphs shorten as heat rises (§5.5), never below 0.3 s.

### 5.4 Commitment: where pileups come from

During COMMIT, a cop locks onto its aim line for 0.6–1.0 s with only small corrections, and **does not avoid other cops, wrecks, or props**. If you dodge:

- The cop **overshoots**: it brakes late, slides past, and may hit whatever was beside you.
- Then it goes into **RECOVER** for 1–1.5 s: a wide turn and a reverse if stuck (reverse recovery already exists). It isn't a threat during this time.

A great dodge creates a pileup: two cops commit to the same point, you drift out, and they meet each other.

### 5.5 Aggression vs competence by heat

| Heat level | Telegraph | Commit time | Attack every… | Prediction lead | Avoids other cops |
| --- | --- | --- | --- | --- | --- |
| 1–2 | 0.6 s | 0.6 s | ~6 s | 0.25 s | Mostly (80%) |
| 3–4 | 0.5 s | 0.8 s | ~4 s | 0.4 s | Half the time |
| 5–7 | 0.45 s | 0.9 s | ~3 s | 0.5 s | Rarely (25%) |
| 8+ | 0.35 s | 1.0 s | ~2 s | 0.55 s | Never while committed |

Each unit also gets a hidden temperament when it spawns. **Rookies** commit longer and brake later. **Veterans** have shorter telegraphs and avoid friendly fire. Mixing them keeps the pursuit unpredictable without being unfair.

### 5.6 Attack tokens: dangerous but readable

The director hands out **attack tokens**. Only token holders may TELEGRAPH and COMMIT. Everyone else positions: flanking, blocking a lane, or following.

| Heat level | 1–2 | 3–4 | 5–6 | 7–8 | 9+ |
| --- | --- | --- | --- | --- | --- |
| Simultaneous attackers | 1 | 2 | 3 | 4 | 5 |

There is a per-unit cooldown of 3–5 s after attacking. This is the trick action games use for melee crowds: the screen *looks* like a mob, but attacks arrive in a readable rhythm. Coordinated moves like a box-in take several tokens at once.

### 5.7 Attack library by unit

- **Patrol:** tailgate, side bump, PIT (level 2+), and a box-in with two others (one each side, one ahead brake-checking).
- **Interceptor:** overtake then brake-check, PIT specialist, and high-speed rear shunts. Fragile: it flies far.
- **Armored SUV:** **ambush T-bone**. It waits at a side-street mouth with a visible pose and lurches out as you pass. It also pins you against walls with a sustained push.
- **SWAT carrier:** drives ahead, deploys spike mats and barrier walls, and forms rolling roadblocks with patrols.
- **Police launcher:** hop-stomp onto you (landing circle); also jumps over wrecks and roadblocks to keep up.
- **Helicopter:** spotlight sweep. While you're lit, cops *ahead* set up roadblocks. Drops flash charges. You can take it down by launching into it (Stomp from below).
- **Tank:** drives in a straight line through everything, crushing cop cars too. Fires slow telegraphed shells. Its own team is its best victim.

### 5.8 Capture becomes physical

Replace "any cop within 7.5 m while slow" with a real **box-in**: two or more cops in contact on different sides, or one cop pinning you against a wall, *and* speed under 7 m/s. The arrest meter fills in 2.5 s. Escapes: Ground Punch, boost, Air Slam shockwave, or a tail whip that breaks a contact.

### 5.9 Tone: nobody gets hurt

Cars are toys. When a cop car wrecks, a tiny low-poly officer pops out (two held poses), shakes a fist, and stomps off the road. Burning wrecks are always empty. Civilians, if added, bail out the same way. This keeps the pastel chaos funny instead of grim.

## 6. Wrecks, fire, and explosions

### 6.1 Overkill decides the wreck type

The damage left over after HP runs out (overkill) decides what happens:

| Overkill | Result |
| --- | --- |
| 0–25 | **Wreck**: smoking and tumbling |
| 25–60 | **Burning wreck**: fuse of 2.5–4 s, then it explodes |
| > 60, or a Stomp | **Instant explosion** after a 0.15 s delayed beat (the "uh-oh" hold) |

Any further hit on a smoking wreck sets it burning. Any hit on a burning wreck detonates it immediately.

### 6.2 Wreck behavior

- Mass 0.8 and low friction, so wrecks slide far and are dangerous obstacles for cops behind.
- Lifetime 15 s, then they sink or fade. The oldest are recycled past the cap of 12.
- Committed cops plow straight into them.

### 6.3 Explosions

| | Value |
| --- | --- |
| Radius | 7 m |
| Damage | 70 at the center, falling off linearly |
| Cop knockback | Up to 18 m/s, biased upward (55% vertical), plus end-over-end spin. Cars do backflips. |
| Player knockback | Up to 10 m/s and 30 damage at the center. Never flips. |
| Chain | Burning wrecks inside the radius detonate after 0.12 s each. |

A chain reads as a stepped domino: *boom… boom… boom*, not one blob. Each link gets its own held starburst.

### 6.4 Fire

Fire patches last 6 s with a 3 m radius. Cops take 15 HP/s and steer away unless committed. You take 5 integrity/s, and boost drives straight through. A burning wreck slid into a crowd spreads patches as it goes.

## 7. The street as a weapon

The weird physics extend into the city. The reference images are full of awnings, hydrants, and parked cars, so use them:

| Object | Behavior |
| --- | --- |
| **Awnings** | **Trampolines.** Land on one and you bounce up at 60% of your landing speed. Free airtime. Cops launched onto them bounce too. |
| **Fire hydrants** | When hit, they shoot a water geyser for 4 s. Driving over one is a mini-launch (8 m/s up). Cops hitting the geyser spin out. |
| **Lamp posts** | Snap and fall across the road over two held poses, becoming a barrier for the cops behind |
| **Parked cars** | Bowling pins with civilian mass. Shove them into pursuers. |
| **Gas station** (landmark) | One huge explosion (radius 18 m) per station per run. A district-level set piece. |
| **Fuel trucks / barrels** (industrial) | Explosive props |
| **Construction ramps** | Free launches without using the punch |
| **Harbor water** | Cops knocked in = a splash takedown. You falling in = WRECKED. |

## 8. Low-FPS rules for vehicles

**Rule zero:** never step *position*. Only orientation, deformation, and effect shapes step. Travel, camera, and physics stay smooth.

| Element | Rate |
| --- | --- |
| Physics, travel, camera, wheel spin | Full frame rate |
| Player chassis poses | 12 pps ("on twos") while cruising |
| Player chassis in **the zone** (combo ×5+) | 24 pps ("on ones") |
| Impact frames for every vehicle | 24 pps for 2 frames |
| Cop chassis poses | 12 pps |
| Tumbling wreck rotation | 12 pps |
| Explosions | 12 pps; starburst held 2 frames |
| Fire | 8 pps, cycling 3–4 poses |
| Hit-stop | Holds everything (§4.7) |

**In the zone.** This is inspired by the much-discussed Spider-Verse choice of keeping Miles on twos until he finds his confidence. The red car could animate on twos normally and switch to ones when you're on a hot combo. The car literally looks more fluid and sure of itself when you're playing well. It's a subtle reward, felt more than seen.

## 9. Color: pastel world, saturated action

The rule: **if it's saturated, it matters.**

| Saturated | Pastel |
| --- | --- |
| Gameplay: the scarlet player car, police red and blue lights, amber attachments and pickups, fire and explosion cores, telegraph circles, spike mats | Everything else: buildings, roads, trees, props, smoke, distant city |

Proposed pastel lift of the style doc's swatches (to be tested):

| Role | Style doc | Pastel proposal |
| --- | --- | --- |
| Warm plaster | #F2D7B6 | #F6E6D0 |
| Peach wall | #E7A18B | #F2BFAE |
| Terracotta | #C97658 | #DDA08A |
| Butter yellow | #E8C666 | #F1DC95 |
| Roof blue | #526E9B | #8EA6C9 |
| Soft teal | #6FA9A1 | #A6CFC7 |
| Leaf green | #709568 | #A5C29A |
| Road slate | #67717A | #858D96 |
| **Player scarlet** | #D94B3D | **#D94B3D (unchanged, the most saturated thing in the city)** |
| Police navy / white | #293D56 / #F7F1E6 | unchanged, for strong identity contrast |

Destruction colors: cream core #F7F1E6, amber #E8AD43, coral #F08A6E, lavender-grey smoke #B9B3C9. Charred wrecks go dusty slate, not black.

## 10. Tuning table: now vs proposed

| Parameter | Now | Proposed |
| --- | --- | --- |
| Contact speed loss | ×0.35 on any hit > 1 m/s | Mass-ratio solver (§4.3) |
| `terminal_impact_speed_mps` | 12 (normal) | 24 normal and near head-on; below that, damage or bounce |
| Player steering at 32 m/s | 100% | 60%, with drift for tight turns |
| Handbrake | Grip 2.3 | Drift state (§3.3) |
| Boost charge while drifting | Slows to 72→36% | No slowdown |
| Gravity | 25 flat | 25; apex hang ×0.55; fall ×1.15 |
| Ground Punch | 24 m/s up, 1.8 s cooldown | Same, plus coyote time, input buffer, and Air Slam at 45 m/s down |
| Patrol speed | 30 + 2.4/tier (≈42 at tier 6) | 28 + 1.2/level, cap 36 |
| Patrol steering | 3.0 rad/s | 2.2, with high-speed falloff |
| Capture | Any cop within 7.5 m while slow | Physical box-in (§5.8) |

## 11. Implementation sketch (Godot 4.7)

- **`ArcadeVehicle`** gains `mass_class`, `health`, `knockback_velocity` (decaying at about 6 m/s²), `stagger_remaining`, and a `drift` sub-state. Velocity = drive + knockback. Remove `forward_speed *= 0.35` and route all contacts through the solver.
- **`ImpactSolver`** (static helper or autoload): called from slide collisions. It de-duplicates each pair per physics frame by instance ID and computes winner, knockback, damage, and hit type. It emits one `impact(a, b, info)` signal for presentation, effects, score, camera hit-stop, and audio.
- **`TumbleProxy`** (pooled `RigidBody3D`): on knockback > 14 m/s, a vertical pop > 6 m/s, or HP ≤ 0, it disables the driver's collision and processing, takes over the presentation node, and inherits linear and angular velocity. When it settles (< 1.5 m/s for 0.5 s): if alive and upright, it hands back to `PoliceVehicle`; otherwise it becomes a wreck.
- **`PoliceBrain`**: the state machine from §5.2 issuing commands to the existing `_drive` executor.
- **`ChaseDirector`**: adds attack tokens, heat, and encounters (see CORE_LOOP §3).
- **Effects**: `Explosion` (Area3D impulse + damage), `FirePatch`, and debris, all pooled and all stepped.

**New checks for `tools/verify.sh`:**
- A normal ram on a patrol wins and keeps more than 70% speed.
- A Ram-state hit keeps more than 85% speed.
- A PIT spins a cop for at least 1 s.
- Cop-on-cop collisions damage both cops.
- A knocked cop returns to driving if upright and alive.
- A turtled cop counts as a takedown.
- A 20° wall scrape at 32 m/s survives.
- A head-on wall hit at 26 m/s is WRECKED.
- Drift charging doesn't reduce speed.
- Air Slam onto a cop produces a Stomp.
- Hit-stop never fires twice within 250 ms.
- The player never ends a landing inverted.

## 12. Moments this should produce

**The Bait.** Two patrols tail you down a neighborhood street. You tap the handbrake into a side street. The lead cop has a token and commits to a PIT at the corner, but you're already drifting past the apex. It overshoots. The second cop is following too closely and rear-ends it: an even hit, and both tumble. One bounces off a blue awning; the other clips a hydrant, and the geyser spins it into the café tables. *PILEUP ×2.* Your drift charged boost the whole time, and you fire it out of the corner.

**The Slam.** A roadblock of two patrols and an SUV fills an intersection, telegraphed a block ahead. You Ground Punch over it, hang at the apex for a breath, see an interceptor racing in from the side street to meet your landing, and Air Slam straight onto it. Crunch: 100 ms of hit-stop and a crushed squash pose. The shockwave tips over one roadblock patrol, which ignites; the burning wreck chains into the SUV. *STOMP! CHAIN ×3.*

**The Tank's Bad Day.** Heat 8. A tank grinds up the avenue behind you, crushing two of its own patrols, which pop like toys. Its turret swings and a closing circle appears just ahead of you. You drift left. The shell lands where you would have been, in the middle of three committed interceptors. They backflip in stepped rotation, and their lightbars spin off ahead of their bodies.

**The Last Mistake.** At 12% integrity and smoking, an SUV lurks at a side street. You see its squat pose but you're mid-boost at 60 m/s, with steering at 45%. You can't turn in time. You T-bone it: in Ram you win, the SUV rolls, and you keep 90% speed straight into the bakery wall, head-on at 58 m/s. WRECKED. The car holds one accordion pose, the trunk pops open, and the results screen appears beside it. You know exactly what you did wrong, and you press restart.
