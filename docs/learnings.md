# Learnings

Decisions and hard-won facts for this project. Written so nobody — human or
agent — has to rediscover them painfully. Append, don't rewrite.

Each entry: what was decided or found, and **why**, because the why is the part
that stops someone undoing it six weeks later.

---

## Locked decisions

These were settled during scoping. Do not relitigate without a reason.

| Decision | Choice | Why |
|---|---|---|
| Render engine | EEVEE Next, 3840×2160 | Cycles at 4K on a 16 GB M1 with an 8-core GPU is 2–6 days for 600 frames. EEVEE Next is an overnight job at worst and looks excellent for an interior. |
| Asset strategy | Script the architecture, source the furniture | Nothing off-the-shelf matches an elliptical room. But scripted upholstery looks stiff and CG, so sofas and soft goods are sourced. |
| Camera | Pivot in place at room centre, 600 frames @ 30 fps | Shows every wall, the windows, the fireplace and the cove. An orbit around the desk leaves most of the room as background blur. |
| Era | Obama 2010 (Michael S. Smith) | Best-documented version, so colours and layout can be matched to reference instead of invented. |
| Interpolation | Linear, no easing | The 360 must loop seamlessly. Easing makes the seam visibly stutter on repeat. |

"4K HDR" was checked with the user and means **HDRI lighting**, not Rec.2100 PQ/HLG
video output. True HDR video export is out of scope.

---

## Environment and tooling

**Blender MCP writes to a live scene.** There is one Blender instance reached
through one socket. This is the single most important constraint on how work is
parallelised — see "Why the modelling is not parallelised" below.

**Build scripts must be idempotent.** Every script deletes the objects it owns
before recreating them. Running phase 3 twice must not produce two floors. This
matters more than usual here because iterating on a look means re-running a
phase many times.

**`execute_blender_code` runs with full user permissions.** The upstream
`weak_sandbox.py` is explicitly not a security boundary — that is upstream's own
wording. Generated code can delete files. Save before running anything
substantial.

---

## Why the modelling is not parallelised

Worth stating plainly because "use more agents" is the obvious instinct and it is
wrong here.

Research and asset sourcing **are** parallel — a dozen independent lookups, no
shared state, ideal for fan-out. That is what the `oval-office-research` workflow
does.

The modelling is **not**. All of it mutates one live Blender scene through one
socket. Two agents building the cove and the fireplace concurrently would
interleave writes into the same `bpy.data` and the last one would win. Worktree
isolation does not help, because the state is a running process, not files in a
git tree. The phases are also genuinely sequential: materials need surfaces,
lighting needs materials, the camera needs the room.

Visual judgement — "is this cove too shallow, is the wallpaper too saturated" —
comes from rendering a test frame and looking at it. That is iterative, not
parallel.

---

## Research sources

| Source | Status |
|---|---|
| Wikipedia | Works with plain WebFetch |
| Wikimedia Commons API | Works with curl. **Send a real User-Agent** or it throttles. |
| `whitehousehistory.org` | **HTTP 403** to WebFetch. Use Chrome MCP. |
| `constructingtheuniverse.com` | **TLS verification fails** in WebFetch. Use Chrome MCP. |

**Date every reference photograph before trusting it.** Photos from 2009 and
earlier show the *Bush-era* decor — a sunburst rug and olive drapes — not the
2010 scheme being modelled. The December 2012 photo has Christmas garland on the
door pediment; ignore it. This trap cost real time already.

---

## Asset sources

**Poly Haven is free.** No account, no key, everything CC0. The $27/year is a
Patreon donation supporting the artists and buys no extra access. Do not suggest
paying for asset access.

**Envato Elements** is subscribed and logged in. `mcp__envato__search_3d` finds
items but **cannot download** — that needs the browser session, so downloads run
through Chrome MCP. Search relevance is loose: a query for "chesterfield sofa"
returned a park bench and a candlestick phone. Judge every result on its title.

**`assets/` is gitignored and the repo is public.** Envato files are licensed to
one personal account. They must never be committed.

---

## The .blend is not source

`*.blend` is gitignored. The scripts in `scripts/` are the source of truth and
regenerate the scene from an empty file.

Committing the .blend was considered and rejected. It is binary, so every save
stores a fresh copy and the repo grows without bound. It would reach hundreds of
megabytes once furniture arrives. And it would still not open correctly for
anyone who cloned, because `assets/` is excluded for licensing reasons — so the
cost buys nothing.

**Never pack external textures into the .blend** (`File > External Data > Pack`).
Packing is what turns a 300 KB file into a 400 MB one. Textures stay in
`assets/` and are referenced by relative path.

The working file is `oval_office.blend` in the project root.
`BlenderMCPTest.blend` was the original default-cube scratch file and is no
longer used.

---

## Blender 5.2 API traps

Confirmed by introspection against the live instance, not from memory. These
changed recently enough that most examples online are wrong.

**The render engine is `BLENDER_EEVEE`, not `BLENDER_EEVEE_NEXT`.** The suffix
was dropped once EEVEE Next became the only EEVEE. `scene.eevee.use_raytracing`
existing is how you confirm you have the new engine. Setting
`"BLENDER_EEVEE_NEXT"` raises an enum error.

**`scene.eevee.use_bloom` no longer exists.** Bloom moved to the compositor in
4.2. Add a Glare node instead of looking for a render toggle.

**`Action.fcurves` is gone.** Blender 4.4 introduced slotted actions and 5.2 has
no legacy fallback, so the attribute raises `AttributeError` rather than
returning empty. Curves now live at:

```python
action.layers[i].strips[j].channelbag(slot).fcurves
```

Use `oo_common.action_fcurves(obj)`, which handles both shapes. This bit once
already while setting keyframe interpolation.

**Auto-smooth is an operator, not a mesh property.** `mesh.use_auto_smooth` was
removed in 4.1. Use `bpy.ops.object.shade_auto_smooth(angle=...)`, which adds a
"Smooth by Angle" modifier. `oo_common.shade_smooth_by_angle` wraps it.

---

## Render output

**PNG sequence into `renders/frames/`, not straight to video.** 600 frames is
long enough that a crash or a laptop sleep partway through must not lose the
lot. Frames already written survive, and the render resumes. ffmpeg encodes to
mp4 afterwards.

View transform is **AgX** with Base Contrast. Filmic is the old default and
crushes the warm interior; Standard clips the window highlights badly.

---

## The 360 rig

An empty at room centre with the camera parented to it. The **empty** is
animated, not the camera, so lens and eye height can be changed without touching
the animation.

**The loop closes because the 360° keyframe sits on frame 601 while the timeline
ends at 600.** Frame 601 would be identical to frame 1, so rendering it doubles a
frame and produces a visible hitch. Verified: frame 600 is at 359.4°, frame 601
at 0°, and the step is a constant 0.6°/frame.

Interpolation is **linear, with VECTOR handles**. Bezier easing makes the seam
stutter, because the speed at the end would not match the speed at the start.

`ORBIT_RADIUS` in `07_camera.py` is **0.0**, a pure nodal pan, which is what was
approved. A small non-zero value (0.3–1.2 m) adds parallax and makes the room
read as more three-dimensional, but is no longer a pivot in place. Worth trying
if the final render feels flat like a panorama.

---

## Cove lighting needs a trough, and the first attempt had none

The first cove-light attempt rendered a flat, unlit room. The cause was
geometric, not a lighting setting: the wall profile ran the cornice straight into
the cove with no gutter, so lamps placed at inset 0.20 m were **inside** wall
geometry sitting at inset 0.302 m. Their light was blocked by the wall itself.

Real cove lighting needs three things in section, and all three matter:

1. A cornice **lip** that projects into the room — here 0.300 m.
2. The lip rising **above** the trough floor (top at z 5.100, floor at 5.055).
   This overhang is what hides the lamps.
3. The cove springing from the **back** of the trough, near the wall plane
   (inset 0.030), so the lamps have room to throw light across it.

Lamps sit at inset 0.130, z 5.075 — above the floor, below the lip top.

**The concealment is verified by sight line, not by eye.** From the camera at
room centre at 1.60 m, a ray grazing the lip's inner top edge (inset 0.240,
z 5.100) is at z 5.174 by the time it reaches the lamp's inset. The lamp at
5.075 sits below that, so it stays hidden through the whole 360. Because the
camera is a pure nodal pivot at the centre, that is the only viewpoint that ever
has to be checked.

28 area lights at 55 W, warm 2900 K. **Shadows are off on all of them** — they
wash a smooth continuous cove and cast nothing meaningful, and 28
shadow-casting lights is a large, entirely wasted cost in EEVEE.

---

## EEVEE Next has no bounce without a baked light probe volume

This is the single most important setting for an interior in EEVEE, and it is
easy to miss because nothing warns you.

EEVEE Next's raytracing is screen-space. Light that leaves the cove and should
come back down the walls never arrives, because the cove is not on screen when
the wall is. The room rendered nearly black and the instinct was to blame the
lamps — wrongly. Adding a **baked** `LIGHTPROBE_VOLUME` covering the room
transformed it.

The volume does nothing until baked:

```python
bpy.ops.object.lightprobe_cache_bake(subset='ACTIVE')  # probe must be active
```

The bake is fast — under a second for an 11,648-sample grid — so re-bake freely.
**Any change to lights, materials or geometry needs a re-bake**, or the room is
lit by a stale cache. Expect confusing results after editing a material if you
forget.

Sizing: slightly larger than the shell, so the samples nearest the walls fall
outside the geometry and do not leak shadow inward.

### The remaining blotches are grid interpolation, and are deliberately not fixed

Soft smudges remain on the walls. The cause was pinned down rather than guessed
at:

- Hypothesis was lamp scalloping. **Tested** by going from 28 lamps to 44,
  changing pool overlap substantially. The blotches were unchanged, so it is not
  the lamps.
- The **wainscot band shows them too**, and that is plain paint with no texture,
  no stripes and no bump. So it is not a material either.

That leaves irradiance-grid interpolation. Raising the grid from 16×18×10 to
26×32×14 softened it without removing it.

It is **left alone on purpose**. Right now every photon on those walls is
probe-derived, because the cove lamps point away from them — an extreme case
that will not exist once daylight comes through the south windows and lamps sit
on the tables. Re-evaluate after phase 2. Raising resolution further is the fix
if it still shows.

---

## purge() must free datablocks, not just delete objects

Deleting an object does **not** free its data. Blender keeps orphaned datablocks
alive, and a new one asking for a name still held silently becomes
`OO_Light_Cove_00.001`. Any later lookup by expected name then fails with a
KeyError.

The first `purge` only cleaned `bpy.data.meshes`, so 29 orphaned lights and 2
cameras accumulated across a few re-runs before it surfaced. It now sweeps
meshes, lights, cameras, curves, metaballs, armatures, lattices and volumes.
`purge_orphans()` is the belt-and-braces sweep for anything already drifted.

Any new object type used in a later phase must be added to `_DATA_COLLECTIONS`.

---

## The camera must tilt up to see the cove

A level camera at eye height never sees the cornice. At 28 mm the vertical
half-angle is 19.9°, so at the south wall 5.46 m away the top of frame is only
z 3.58 m — and the cornice starts at 4.62 m. The first lit test render was a
featureless wall for exactly this reason, not a lighting fault.

Now 24 mm with a 7° tilt. This needs revisiting once there is furniture, because
tilting up trades away floor — and the rug, which carries the presidential seal
and the quotations, is on the floor.

---

## World.use_nodes is deprecated

Blender warns it will go in 6.0. Harmless now; if this project is ever reopened
on a later build, the world setup in `06_lighting.py` is the thing that breaks.

---

## Read the reference before trusting a written description

Eric Gugler's cornice is described everywhere as "deep bracketed". Built from
that description it came out as heavy modillion brackets — and cropping the
reference photograph to the cornice showed something completely different: two
delicate enrichment courses, small oval paterae over a bead-and-dentil course at
half the pitch. The invented version was wrong by about a factor of two in every
dimension.

**Crop and enlarge the reference photographs before modelling any detail.**
`sips` does this fine and is already on the machine; PIL is not installed.

```bash
sips -c <h> <w> --cropOffset <top> <left> in.jpg --out crop.png
sips -z <h> <w> crop.png
```

Anything repeated around the wall must be spaced by **arc length**, not by the
ellipse parameter. Uniform `t` crowds items at the ends of the long axis and
spreads them east and west, which reads as a mistake even to someone not looking
for it. Use `oo_common.t_by_arclength`.

---

## Gitignore negations do not cross directories

`*.png` plus `!reference/*.png` silently dropped everything under
`reference/progress/`. A single `*` does not match a subdirectory, and nothing
errors — the files just never appear in a commit. It now reads
`!reference/**/*.png`.

Worth checking `git status` actually lists a new file rather than assuming
`git add -A` caught it.

---

## Verified room measurements

Confirmed against Wikipedia and the White House Historical Association.

| Quantity | Imperial | Metric |
|---|---|---|
| Long axis (N–S) | 35 ft 10 in | **10.922 m** (semi-axis 5.461 m) |
| Short axis (E–W) | 29 ft | **8.839 m** (semi-axis 4.420 m) |
| Ceiling at centre | 18 ft 6 in | **5.639 m** |
| Cove springs at | 16 ft 7 in | **5.055 m** |
| Circumference | ~102 ft 5 in | ~31.2 m |
| Floor area | ~816 sq ft | ~75.8 m² |

**Axis convention for this project:** room centre is the origin. **−Y is south**
(the window wall, behind the desk), **+Y is north** (the fireplace). The long
axis runs N–S along Y, the short axis E–W along X. Compass bearings in research
notes are given in degrees from due south.

**The room is a true ellipse**, not a stadium shape or a composite of arcs.

---

## Architecture facts that are easy to get wrong

**There are no ceiling light fixtures.** Bulbs concealed in the cornice wash
light upward onto the cove. This indirect wash is the single biggest reason the
room photographs the way it does. Modelling a chandelier or downlights would be
wrong and would look wrong.

**The cove is the room's signature.** A 360° camera at eye height spends much of
its time looking at it. It deserves the geometry budget.

---

## Modelling budget

16 GB unified memory, 8-core M1 GPU. Real constraints:

- **Textures cap at 2K.** 4K texture sets across a full interior will thrash.
- **Carved relief goes in as normal and bump maps, not geometry.** The Resolute
  desk panels, the plaster medallion, the niche shell heads, the cornice dentils
  where distant. At the camera distances involved the difference is invisible and
  the polygon cost is not.
- The exception is silhouette. Anything that breaks the outline against a
  background — the cove curve, the pediment profiles, the mantel shelf — must be
  real geometry, because normal maps do not change a silhouette.
