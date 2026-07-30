# Oval Office in Blender

A detailed 3D model of the White House Oval Office, built procedurally in
Blender through the [Blender MCP server](https://projects.blender.org/lab/blender_mcp),
plus a 20-second animation in which the camera turns a full 360° from the centre
of the room.

The room is modelled as it looked after the 2010 redecoration by Michael S.
Smith — café-au-lait striped wallpaper, burgundy drapes, olive velvet sofas, and
the cream rug with quotations around its border.

## Status

Design approved, implementation not yet started. See
[the spec](docs/superpowers/specs/2026-07-30-oval-office-design.md).

## How it is built

The architecture is scripted rather than sourced, because nothing off-the-shelf
matches an elliptical room. Each build phase is an idempotent Python script in
`scripts/`, so any stage can re-run without duplicating geometry.

Measurements come from the White House Historical Association and Wikipedia:
the ellipse is 35 ft 10 in × 29 ft, with the ceiling 18 ft 6 in at its centre.

Rendering targets EEVEE Next at 3840×2160, 30 fps.

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
