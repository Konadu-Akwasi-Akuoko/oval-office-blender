# Oval Office — model and 360° animation

**Date:** 2026-07-30
**Status:** approved

## Goal

Build a detailed 3D model of the White House Oval Office in Blender and render a
20-second animation in which the camera turns a full 360° from the centre of the
room. Output is 3840×2160 at 30 fps.

## Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Render engine | EEVEE Next | On a 16 GB M1 with an 8-core GPU, Cycles at 4K would take days per animation. EEVEE Next renders the same 600 frames overnight at worst and looks excellent for an interior. |
| Asset strategy | Hybrid | Nothing off-the-shelf matches an elliptical room, so the architecture is scripted. Scripted upholstery looks stiff, so sofas and similar are sourced. |
| Camera | Pivot in place at room centre | Shows every wall, the windows, the fireplace and the ceiling cove. An orbit around the desk would leave most of the room as background blur. |
| Era | Obama 2010 | The best-documented version, so colours and layout can be matched to reference rather than invented. |

"HDR" here means HDRI lighting through the windows, not Rec.2100 video output.
That was checked and is out of scope.

## Verified measurements

Sourced from Wikipedia and the White House Historical Association.

- Ellipse 35 ft 10 in × 29 ft — semi-axes **5.461 m × 4.420 m**
- Ceiling **5.64 m** (18 ft 6 in) at centre
- Cove springs at **5.05 m** (16 ft 7 in)
- Floor area ~816 sq ft, circumference ~102 ft 5 in

## Architecture

The shell is a true ellipse. Walls rise to a deep bracketed cornice with a
dentil course, above which a cove carries the ceiling from 5.05 m to 5.64 m at
the centre. A plaster medallion installed in 1934 sits at the apex and carries
elements of the presidential seal.

**Openings.** Three tall multi-pane windows on the south wall behind the desk.
Four doors, each under a full triangular pediment: east to the Rose Garden, west
to the private study, northwest to the West Wing corridor, northeast to the
secretary's office. Two arched niches with carved shell heads serve as
bookcases. A neoclassical marble mantel, made for Taft in 1909 and salvaged
after the 1929 West Wing fire, sits on the north wall.

**Surfaces.** Floor is quarter-sawn oak and walnut in a contrasting cross
pattern, laid in 2005, with a perimeter border. A painted wainscot about 0.9 m
high with recessed panels runs below the wallpaper line.

## Furnishings — 2010 scheme

Custom-modelled, because these define the room:

- **Resolute desk.** Carved relief panels go in as normal maps, not geometry.
- **Rug.** Cream and wheat, presidential seal centred, five quotations around a
  blue-grey border — Lincoln, Kennedy, both Roosevelts, and Martin Luther King Jr.

Sourced from Envato or Poly Haven:

- Two olive-brown velvet sofas, walnut coffee table, cane-back armchairs
- Mahogany chest, desk chair, table lamps, books, the Remington bronze

Artwork is composited from public-domain photographs onto framed planes: Childe
Hassam's *The Avenue in the Rain*, the Rockwell Statue of Liberty, the Lincoln
portrait.

**Colours.** Café-au-lait and buff wallpaper in three-inch stripes, hand-painted
by Elizabeth Dow's studio. Burgundy drapes with valances over each window.

## Lighting

The room has no ceiling fixtures. Bulbs concealed within the cornice wash light
upward onto the cove, and that indirect wash is what gives the room its
characteristic look. The model reproduces it with emissive strips in the
cornice, an HDRI sun through the south windows, and warm table lamps as accents.

EEVEE Next needs raytraced global illumination, screen-space reflections and
soft shadows enabled for this to read correctly.

## Camera animation

An empty at room centre with the camera parented at 1.6 m eye height, roughly
28 mm focal length — wide enough to take in the cove without distorting the
ellipse. The empty rotates 360° across 600 frames at 30 fps. Interpolation stays
linear so the loop is seamless; easing would make the start and end visibly
stutter on repeat.

## Build phases

Each phase is an idempotent Python script in `scripts/`, so any stage can re-run
without duplicating geometry.

1. Shell — ellipse, floor, wainscot, cornice, cove, ceiling medallion
2. Openings — windows, doors, pediments, niches, fireplace
3. Materials — wallpaper, parquet, paint, marble
4. Furniture — custom Resolute desk, then sourced pieces
5. Props and art
6. Lighting
7. Camera and animation
8. Render

## Layout

```
scripts/      idempotent build scripts, one per phase
reference/    public-domain photographs, committed
assets/       downloaded models — gitignored, licensed to the account
docs/         this spec
renders/      output — gitignored
```

## Constraints and risks

- **Memory.** 16 GB unified on an M1. Textures cap at 2K. Polygon budget is
  deliberate, and carved relief goes in as normal and bump maps rather than
  geometry — at this camera distance the difference is invisible and the cost is
  not.
- **Envato downloads** need the logged-in browser session, so that step runs
  through Chrome automation rather than an API call.
- **Reference dating.** 2009 photographs still show the Bush-era sunburst rug
  and olive drapes. Only 2010 and later show the scheme being built.
- **Licensing.** The repo is public. `assets/` is gitignored and must stay that
  way.
