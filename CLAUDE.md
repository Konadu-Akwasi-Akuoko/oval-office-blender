# Read this first

**[`docs/learnings.md`](docs/learnings.md) holds every decision made on this
project and why.** Read it before doing any work here. It records the locked
decisions, the verified measurements, the axis convention, which sites block
WebFetch, and the traps that have already cost time.

Append to it whenever you decide something a future agent would otherwise have
to rediscover painfully. It is written to survive context compaction — if it is
only in the conversation, it is already lost.

# How to work on this project

**Work autonomously until the whole thing is finished.** Do not stop to ask
whether to continue, do not check in at the end of each phase, and do not hand
back a partial result waiting for approval. Keep going until the render exists.

Ask only when genuinely blocked on something no reasonable assumption can
settle — a licensing question, a decision that would be expensive to undo, or
credentials. Everything else: pick the sensible option, write down why in
`docs/learnings.md`, and carry on.

**Commit at every working milestone** and push. Commit messages explain the why,
especially for bugs that failed silently.

**Track the work with the task tools.** `TaskCreate` up front, `TaskUpdate` to
`in_progress` when starting and `completed` when genuinely done. Never mark
something completed that is partial, untested, or broken — leave it
`in_progress` and create a task describing the blocker.

**Verify before claiming.** Render it and look at the image. Raycast the
geometry. Count the faces. Several bugs on this project failed silently and
looked fine until measured — see `docs/learnings.md`.

# Rendering

**Read frames while the render runs — every ~50 frames, not just at the end.**
Each frame is a different angle of the 360, so a fault can sit in a region no
earlier still render ever covered. Two real problems were caught this way at 40%
that would otherwise have surfaced only in the finished film. Checking a frame
costs seconds.

```bash
cp renders/frames/oo_0238.png /tmp/check.png && sips -Z 1250 /tmp/check.png
# frame N is (N-1) * 0.6 degrees into the rotation
```

**If a frame looks wrong, STOP the render, fix it, and start again.** Do not
reason that something is "a fidelity gap rather than a bug" and let a flawed
render finish — that judgement was made once here and it was the wrong call.
Discarded frames are cheap; a finished film with a visible fault is not. The
whole point of checking early is to act on what you find.

Restarting costs only the frames already done. At about 21 s/frame, stopping at
40% throws away roughly 85 minutes — always less than rendering twice.

# Subagents

**Always use Opus for subagents on this project.** Pass `model: 'opus'`
explicitly on every `agent()` call in a workflow and on every `Agent` tool call,
rather than relying on inheritance from the session model.

The work here is research judgement — dating a photograph correctly, rejecting a
sofa that is the wrong period, estimating a dimension from a reference — and a
smaller model gets those wrong in ways that are expensive to detect later. A bad
measurement propagates into geometry and is only caught when something looks
wrong in a render.

# Blender MCP setup

Notes for working with the official Blender MCP server on this machine.
Two things here deviate from the upstream docs — see "Deviations" below.

## Components

The project ships as two halves that talk over a local TCP socket:

| Piece | Runs in | Location |
|---|---|---|
| Blender add-on | Blender itself | installed from `~/Downloads/mcp-1.0.0.zip` |
| MCP server | separate process, launched by the MCP client | `~/Projects/blender_mcp/mcp/` |

Both must be present. The add-on alone does nothing, and the server has
nothing to talk to without it.

## Install state

- Blender 5.2.0 LTS, installed via Homebrew (`brew upgrade --cask blender` to update)
- Server repo cloned from https://projects.blender.org/lab/blender_mcp.git
- Add-on requires Blender 5.1 or newer — enforced by `blender_manifest.toml`

## MCP client config

```json
{
  "mcpServers": {
    "blender": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/akwasikonaduakuoko/Projects/blender_mcp/mcp",
        "run",
        "blender-mcp"
      ]
    }
  }
}
```

## Deviations from upstream docs

### 1. Repo lives in ~/Projects, not ~

The setup wiki clones to `$HOME/blender_mcp` and its example config uses
`$HOME/blender_mcp/mcp`. This machine uses `~/Projects/blender_mcp` instead.
The `--directory` argument is the only value that has to change.

### 2. The mcp SDK is pinned to v1

`mcp/pyproject.toml` upstream declares `mcp[cli]>=1.2.0` with no upper bound.
That resolves to SDK 2.0.0, which removed `mcp.server.fastmcp` and makes the
server fail on import:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

The local fix pins it:

```toml
"mcp[cli]>=1.2.0,<2",
```

This is an upstream bug, not a local misconfiguration. Drop the pin and
re-test after upstream migrates to the v2 API; revert with
`git checkout mcp/pyproject.toml`.

## Gotchas

- **Moving the repo breaks the venv.** `uv` bakes absolute paths into
  `.venv/bin/*` shebangs. After any move, run `rm -rf .venv` in `mcp/` and let
  `uv run` rebuild it.
- **Blender must be launched once before installing the add-on.** The config
  directory under `~/Library/Application Support/Blender/<version>/` does not
  exist until a launch completes.
- **Enable auto-start** in the add-on preferences, otherwise the socket server
  has to be started by hand every session.

## Security

`addon/blender_mcp_addon/weak_sandbox.py` is not a security boundary — the name
is upstream's own wording. Code generated through `execute_blender_code` runs
with full user permissions: it can delete or overwrite files, read paths
referenced by the `.blend`, change preferences, and make network calls. Save
work before running generated scripts, and prefer scratch files over anything
that matters.

## Assets

### Poly Haven — free, no account

Open API. No key, no login, everything CC0:

- `https://api.polyhaven.com/assets?type=models` — catalog
- `https://api.polyhaven.com/files/<slug>` — download URLs, including native `.blend`

The $27/year Poly Haven membership is a Patreon donation to support the
artists. It buys no extra access. Do not suggest paying for asset access here.

Prefer this over browser automation.

### Envato Elements — paid, account already active

The account is subscribed and logged in as Akwasi Konadu. Two ways in:

- **`mcp__envato__search_3d`** finds items and returns listing URLs. Filter on
  `three_d_file_types: "BLEND"` and `three_d_has_textures: true`. Search
  relevance is loose — "chesterfield sofa" also returns a park bench and a
  candlestick phone — so scan results rather than trusting the top hit.
- **Downloads need the logged-in browser session.** The MCP tool cannot fetch
  files. Drive Chrome via the `mcp__claude-in-chrome__*` tools to download.

Store every downloaded asset in `assets/` in the project. Envato files are
licensed to this account, so `assets/` is gitignored and must never be
committed — this repo is public.

Sketchfab needs a login and its licenses vary per model, so download those
manually rather than scripting them.

### Reference images

Wikimedia Commons for anything US-government — White House photographs are
public domain and safe to commit. Query the API directly rather than scraping:

```
https://commons.wikimedia.org/w/api.php?action=query&generator=search
  &gsrsearch=<terms>&gsrnamespace=6&prop=imageinfo
  &iiprop=url|extmetadata&iiurlwidth=1800&format=json
```

Send a real `User-Agent` or Wikimedia throttles the request. Check
`extmetadata.LicenseShortName` before committing anything.

## Web research

- `whitehousehistory.org` returns **403** to WebFetch. Use the Chrome MCP tools
  for it.
- `constructingtheuniverse.com` fails TLS verification in WebFetch. Same fix.
- Wikipedia and the Commons API both work fine with plain WebFetch/curl.

## Oval Office project

Building a detailed model plus a 360° camera animation. Decisions already made,
so do not relitigate them:

| Decision | Choice |
|---|---|
| Render engine | EEVEE Next, 3840×2160 |
| Asset strategy | Script the architecture, source the furniture |
| Camera | Pivot in place at room centre, 600 frames @ 30 fps |
| Era | Obama 2010 redecoration (Michael S. Smith) |

### Verified dimensions

- Ellipse **35 ft 10 in × 29 ft** — semi-axes 5.461 m × 4.420 m
- Ceiling **18 ft 6 in** (5.64 m) at centre, cove springs at **16 ft 7 in** (5.05 m)
- Floor area ~816 sq ft, circumference ~102 ft 5 in

### Architecture

Three south windows behind the desk. Four doors — east to the Rose Garden,
west to the private study, northwest to the corridor, northeast to the
secretary's office — each under a full triangular pediment. Two arched niches
with carved shell heads serve as bookcases. Marble mantel on the north wall,
made for Taft in 1909. Plaster ceiling medallion from 1934 carrying elements of
the presidential seal. Floor is quarter-sawn oak and walnut in a cross pattern,
laid 2005.

**There are no ceiling fixtures.** Bulbs concealed in the cornice wash light
upward onto the cove. Reproduce this with emissive strips — it is why the room
photographs the way it does.

### 2010 decor

Café-au-lait and buff wallpaper, hand-painted by Elizabeth Dow's studio, in
three-inch stripes. Burgundy drapes with valances. Two olive-brown velvet
sofas. Walnut coffee table. Cream and wheat rug, presidential seal centred,
five quotations around a blue-grey border — Lincoln, Kennedy, both Roosevelts,
and King.

### Reading the reference photos

Check the date before trusting any photo. The 2009 images still show the
**Bush-era** sunburst rug and olive drapes. Only 2010 and later show the scheme
being built. The December 2012 photo has Christmas garland on the door
pediment — ignore it.

### Modelling budget

16 GB M1, 8-core GPU. Cap textures at 2K. Carved relief — the desk panels, the
plaster ornament, the niche shells — goes in as normal and bump maps, not
geometry. Scripts in `scripts/` must be idempotent so any phase can re-run
without duplicating objects.
