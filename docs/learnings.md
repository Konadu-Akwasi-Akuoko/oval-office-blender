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
