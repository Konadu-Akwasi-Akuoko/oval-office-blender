# Oval Office in Blender

A detailed 3D model of the White House Oval Office, built procedurally in
Blender through the [Blender MCP server](https://projects.blender.org/lab/blender_mcp),
plus a 20-second animation in which the camera turns a full 360° from the centre
of the room.

The room is modelled as it looked after the 2010 redecoration by Michael S.
Smith — café-au-lait striped wallpaper, burgundy drapes, olive velvet sofas, and
the cream rug with quotations around its border.

## Status

Room built and rendering. The full 600-frame 4K animation takes about
3.5 hours on an M1 at 20.9 s/frame.

## Building it

Open `oval_office.blend` in Blender 5.2 with the MCP add-on, then:

```python
exec(open("scripts/build_all.py").read())
```

That rebuilds the entire room from nothing in under a second. Then:

```bash
python3 scripts/fetch_polyhaven.py    # free CC0 assets, ~83 MB
./scripts/encode.sh                   # PNG sequence to mp4, after rendering
```

**Phase order is load-bearing** and lives in `build_all.py`. Three separate
silent bugs came from getting it wrong — see `docs/learnings.md`.

| Phase | Builds |
|---|---|
| `01_shell` | Elliptical wall, cornice profile, cove, floor, ceiling |
| `02_joinery` | 126 modillions, rosettes, 252 egg-and-dart |
| `02b_openings` | Windows, doors, pediments, jib doors |
| `02c_niches` | Four arch-and-shell units |
| `04_fireplace` | Taft mantel and breast |
| `05_desk` | Resolute desk |
| `05b_rug` | 2010 rug, seal, border quotations |
| `05c_furniture` | Sofas, tables, chairs, lamps, flags |
| `03_materials` / `03b_pbr` | Procedural materials, then PBR overrides |
| `06_lighting` | Cove lamps, sun, HDRI, light probe volume |
| `07_camera` | 360 rig and render settings |

## Accuracy

Measurements come from the White House Historical Association and Wikipedia:
the ellipse is 35 ft 10 in × 29 ft, ceiling 18 ft 6 in. Verified in the model at
8.840 × 10.922 m with 75.8 m² of floor, against the published 816 sq ft.

Finer detail — the cornice profile, the modillion count, the ceiling medallion —
comes from a 14-agent research pass that solved them photogrammetrically against
an upward-looking 2022 ceiling photograph. Every claim carries its own
confidence in [`docs/research-findings.md`](docs/research-findings.md);
`estimated` means derived from photographs, not from a published measurement.

Rendering is EEVEE Next at 3840×2160, 30 fps.

## Layout

| Path | Contents |
|---|---|
| `scripts/` | Build scripts, one per phase |
| `reference/` | Public-domain White House photographs |
| `docs/` | Design spec |
| `assets/` | Downloaded models — not committed |
| `renders/` | Output — not committed |

## Licensing

Reference photographs in `reference/` are works of the US federal government and
are in the public domain.

`assets/` holds models downloaded under a personal Envato Elements
subscription. Those are licensed to an individual account and are excluded from
this repository. You will need your own source for them.

Code in this repository is MIT licensed.
