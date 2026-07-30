# Assets

`assets/` is gitignored. This file is the manifest, so a fresh clone knows what
it needs and where to get it.

## Poly Haven — free, scripted

```bash
python3 scripts/fetch_polyhaven.py
```

CC0, no account, no key, no payment. About 83 MB at 2K.

| Asset | Type | Used for |
|---|---|---|
| `herringbone_parquet` | texture | Floor |
| `dark_wood` | texture | Resolute desk, mahogany chest |
| `velour_velvet` | texture | Sofas |
| `dirty_carpet` | texture | Rug weave base |
| `beige_wall_001` | texture | Plaster |
| `symmetrical_garden_02` | HDRI | Daylight through the south windows |
| `vintage_grandfather_clock_01` | model | Tall case clock |

The Poly Haven membership is a donation supporting the artists. It buys no
extra access and is not needed.

## Envato Elements — manual, licensed per account

These cannot be scripted. `mcp__envato__search_3d` finds items but the download
needs a logged-in browser session. Files are licensed to one personal
subscription and **must never be committed**.

Download each into `assets/envato/<slug>/`.

| Item | Title | Link |
|---|---|---|
| Sofa | Velvet Classic Sofa | needs a skirt built and a recolour |
| Armchair | Classic Armchair | |
| Cane-back side chair | Guinevere Anglo Indian Regency chair | |
| Desk chair | Executive Black Leather Office Chair | |
| Coffee table | Rectangular wooden coffee table | poor match — see gaps |
| Chest of drawers | Ornate Wood Dresser with Pulls | |
| Side table | Wood Side Table with Drawer | |
| Table lamp | Marmon 32" Table Lamp With Shade | |
| Books | Row of Classic Books | |
| Vase | Beige Clay Vase | |
| Flag | United States Cloth Flag Stand Gold | |
| Potted plant | Ficus Benjamin | |
| Marble | White Marble Stone Patterns | fireplace mantel |

Full candidate lists with rankings and rejection reasons are in
`research-findings.md`.

## Hand-modelled

Nothing in either library matches these, so they are built in `scripts/`.

- **Resolute desk** — a specific 1880 object, no substitute exists
- **The rug** — presidential seal and five border quotations
- **Sofas** — the Obama sofas are large, plainly tailored, rolled-arm and
  skirted to the floor in olive damask. Nothing has all four traits. Every
  candidate needs a skirt built and a recolour, so hand-modelling may win.
- **Coffee table** — the real gap. Candidates are near-square, grey-taupe, or
  glass-topped with Anglo-Indian legs. None is a rectangular walnut table.
- **Remington "Bronco Buster" bronze** — no acceptable match anywhere.
