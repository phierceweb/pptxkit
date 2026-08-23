# The CLI — every command, and the knobs behind them

Reference for the twelve `pptxkit` commands and the environment variables they read. Run
them through `bin/run`, which uses the project venv:

```bash
bin/run <command> [args]
```

`bin/run` also resolves pf-core's own console scripts from the venv — `bin/run pf-doctor`
attests the install (loaded copy, extras, env resolution, docs link) and is what `bin/setup`
points at when it finishes. See `docs/pf-core/doctor.md` — a symlink `bin/setup`
creates into the installed pf-core's own docs, so it exists after setup, not on GitHub.

For the workflow these commands compose into — build, look, fix, rebuild — read
[`docs/pptx-deck-building.md`](pptx-deck-building.md). This doc is the surface
reference.

---

## Table of Contents

- [Global options](#global-options)
- [`new` — start a deck](#new--start-a-deck)
- [`build` — spec to deck](#build--spec-to-deck)
- [`demo` — every capability in one deck](#demo--every-capability-in-one-deck)
- [`render` — deck to images](#render--deck-to-images)
- [`qa` — check a built deck](#qa--check-a-built-deck)
- [`diff` — what a hand-edit changed](#diff--what-a-hand-edit-changed)
- [`inspect` — inventory a deck's shapes](#inspect--inventory-a-decks-shapes)
- [`conform` — onboard a brand template](#conform--onboard-a-brand-template)
- [`shot` — screenshot an HTML file](#shot--screenshot-an-html-file)
- [`sample` — a template to onboard against](#sample--a-template-to-onboard-against)
- [`doctor` — what this install can do](#doctor--what-this-install-can-do)
- [`glyphs` — the built-in icon set](#glyphs--the-built-in-icon-set)
- [Environment variables](#environment-variables)
- [External tools](#external-tools)
- [Exit codes and logging](#exit-codes-and-logging)
- [Adding a command](#adding-a-command)

## Global options

Two options belong to the tool rather than to a command, so they go **before** it:

| Option | Effect |
|---|---|
| `-v` / `--verbose` | Debug logging: `bin/run -v build deck.deck.yaml`. |
| `-V` / `--version` | Print the installed version and exit: `bin/run --version`. |

`doctor` prints the same version as its first row, beside everything else about the
install.

## `new` — start a deck

```bash
bin/run new "Q4 Review"
bin/run new q4-review --theme brand --no-build
```

Writes `authoring/<slug>/<slug>.deck.yaml` and builds it, so the first thing you have
is a deck you can open and a spec you can edit.

Both paths are relative to the current directory, so run outside a checkout it
creates `authoring/` and `out/` where you stand. `--root` moves the source
directory; the build goes wherever the spec's `out:` points.

| Flag | Effect |
|---|---|
| `--theme` / `-t` | Theme the deck names. Default `base`. |
| `--root` | Where the deck's source directory goes. Default `authoring/`. |
| `--build` / `--no-build` | Compile it straight away. On by default. |

The slug keeps letters and digits only, so `Q1/Q2 Review` becomes `q1q2-review` and a
deck never writes outside the `--root` it was given; `/ \\ :` become `-` in the built
deck's filename while the title keeps them. A name that leaves no slug at all is
refused with `a deck needs a name`. A build that fails frees the name it just wrote,
so the retry is not blocked by the directory the first attempt left.

**The scaffold is a working deck, not a stub** — six slides covering the shapes most
decks are made of: a cover, a section divider, bullets with a click build, a `split:`
row of cards, a native chart, and a closing. Each carries one line saying what to
change. Editing something that runs is how these actually get written; composing the
first one from an empty buffer means reading the wire format, the component index and
the placement rules before writing a word.

`"Q4 Review"` and `q4-review` give the same deck — spaces, hyphens and underscores all
slug the same way, and a word keeps the case you typed past its first letter, so
`ML-pipeline` titles as *ML Pipeline*.

It never overwrites. A deck of that name already there is an error naming it, because
this is the one command that would destroy work by succeeding.

## `build` — spec to deck

```bash
bin/run build deck.deck.yaml
bin/run build deck.deck.yaml --theme templates/acme.theme.yaml --out out/deck/deck-v3.pptx
```

Compiles a `.deck.yaml` against a theme into a `.pptx` and two siblings.
`<deck>.manifest.json` records every shape's box, colours and font size — it is what
`qa` reads, so keep the pair together. `<deck>.content.md` is the same build rendered
as the deck's **words**: slide by slide, chrome as headings, tables as tables, speaker
notes as quotes. Read that one; it is derived, so regenerate it rather than edit it.

| Flag | Effect |
|---|---|
| `--theme` / `-t` | Theme file. Default: resolved by the spec's `theme:` name against the theme directory. |
| `--out` / `-o` | Output path, overriding the spec's own `out:`. |
| `--keep-layouts` | Keep the template's unused slide layouts and masters, and the media only they reach. Off by default. |

A brand template arrives with every layout its designer drew, and a built deck uses
one of them. The rest are dropped along with the media nothing else reaches — on a
real template that is most of the file, and one of those layouts is often a format
Keynote refuses to import. Pass `--keep-layouts` when you intend to hand-edit the
built deck in PowerPoint and want its other layouts available.

The spec format is [`docs/authoring.md`](authoring.md).

## `demo` — every capability in one deck

```bash
bin/run demo
bin/run demo --theme brand --out out/demo
```

Builds **every capability the library has** into one deck, against any theme you name:
every component, chrome treatment, chart kind, table variant, photograph case and
motion build.

| Flag | Effect |
|---|---|
| `--theme` / `-t` | Theme name, resolved against the theme directory. Default `base`. |
| `--out` / `-o` | Where the deck goes. Default `out/demo`. |

**It is generated, not written.** The catalogue is `EXERCISE` in
`src/pptxkit/conform/exercise.py` — the same slides `conform` drives against real
brand templates. Nothing here is a second copy: [`testing.md`](testing.md)
requires every new capability to land in that registry, and `tests/test_templates.py`
builds all of it against every brand template in `templates/`. So the demo grows
with the library, and a
capability cannot go missing from it without the suite going red.

That is why it replaced a hand-written deck. A written one pins a theme, a set of
words and a placement per capability, and goes silently stale the day a component is
added. This one pins nothing — name a different theme and the same catalogue renders
through it.

Read the result with the `.content.md` written beside it rather than by opening every
slide. If a capability fails against a brand theme the build stops at it; reach for
`conform`, which builds each alone and reports every failure rather than the first.

## `render` — deck to images

```bash
bin/run render out/deck/deck.pptx
bin/run render out/deck/deck.pptx --contact-sheet --dpi 140
```

Converts the deck to PDF with headless LibreOffice, then rasterizes each page with
`pdftoppm` into `<pptx-dir>/render/<deck>/slide-N.jpg` — a directory per deck, so a
version series beside it never overwrites these — zero-padded to the deck's own
length — `slide-07.jpg` in a 69-slide deck, `slide-007.jpg` in a 111-slide one, so a
glob wants `slide-*.jpg` rather than a fixed width. **This is how you look at a deck** —
the render is the ground truth, not the spec.

| Flag | Effect |
|---|---|
| `--outdir` / `-o` | Where images go. Default `<pptx-dir>/render/<deck>`. |
| `--dpi` | Rasterization DPI. Default 110, or `$PPTXKIT_RENDER_DPI`. |
| `--contact-sheet` | Also write `contact_sheet.png`, the whole deck as one grid. |
| `--cols` | Columns in that grid. Default 4. |

Stale `slide-<n>.<image>` files a previous render wrote are removed first, so a shorter
deck never leaves orphans from a longer one behind — anything else in the directory,
including `contact_sheet.png` and `qa.md`, is left alone. Each run gets its own
LibreOffice profile, so concurrent renders do not silently no-op against a shared lock.

## `qa` — check a built deck

```bash
bin/run qa out/deck/deck.pptx
bin/run qa out/deck/deck.pptx --fail-on warn --no-render
```

Checks geometry, typography, contrast and overflow against the build manifest, prints
one line per finding, and writes `qa.md` / `qa.json`.

| Flag | Effect |
|---|---|
| `--manifest` / `-m` | Default `<deck>.manifest.json`. |
| `--theme` / `-t` | Default: the theme recorded in the manifest. |
| `--no-render` | Skip the render-based overflow and contrast checks — much faster, much weaker. |
| `--fail-on` | Exit 1 at this severity or worse: `error`, `warn` or `info`. |
| `--outdir` / `-o` | Where `qa.md` / `qa.json` go. Default `<deck-dir>/render/<deck>`. |

With no LibreOffice on the machine the command fails rather than quietly checking less,
and says to re-run it with `--no-render` — bounds, placement, reserved regions, type
sizes and contrast need no external tool.

Without `--fail-on` the command reports and exits 0, so it is safe in a loop; with it, it
is a gate. What the checks do and do not catch is [`docs/qa.md`](qa.md) — read the
"cannot catch" section before trusting a clean run.

## `diff` — what a hand-edit changed

```bash
bin/run diff "out/my-deck/My Deck v3.pptx"
bin/run diff "out/my-deck/My Deck v3.pptx" --out out/my-deck
```

```
Deck v3.pptx was edited after its build from authoring/deck/deck.deck.yaml
  slide 1  moved    s1.chrome.title  0.8,0.375 11.733×1.05in → 1.55,0.375 11.733×1.05in
  slide 1  retyped  s1.chrome.title  'Smoke Test' → 'Smoke Test, revised'
  slide 1  added    TextBox 3        not in the build — added by hand, so no placement made it
  slide 1  gone     s1.bg#1          the build drew this and the deck no longer has it
```

Editing a delivered deck in PowerPoint is a sanctioned workflow here — rebuilding
throws the edit away. This is how you see **what** was edited, so it can go back into
the spec rather than living only in the binary.

| Flag | Effect |
|---|---|
| `--manifest` / `-m` | Default `<deck>.manifest.json`. |
| `--out` / `-o` | Also write `readback.md` in this directory. |

It works because shapes are named for the spec node that drew them and PowerPoint
keeps a shape name through an edit — see
[what the manifest records](qa.md#what-the-manifest-records). Matching runs from the
deck's side, since one shape can answer for several records: chrome's stacked lines
are paragraphs in a single frame.

**What it cannot see:** a colour, a font, a point size, or anything inside a table
cell — cells were never shapes, so they carry no name. A deck whose bytes changed with
no shape difference says so rather than reporting nothing.

## `inspect` — inventory a deck's shapes

```bash
bin/run inspect "out/my-deck/My Deck v3.pptx"
```

```
deck.pptx: 36 slide(s)
slide 1 (Blank)
  id=2    0.00,0.00 13.33×7.50     's1.bg#1'
  id=3    0.80,0.38 11.73×1.05     's1.chrome'
```

Every slide's shapes with ids, names and inch boxes. This is the tool for **surgical
hand-edits to a delivered deck**: it works on any `.pptx`, needs no manifest, and the
shape ids it prints are what a python-pptx patch script targets.

A deck pptxkit built names each shape for the spec node that drew it — `s1.chrome`,
`s3.hero.card#1` — so the name says what to edit and where it came from. On a deck
from anywhere else the names are whatever PowerPoint assigned (`Rectangle 1`).
Names are the stable handle; ids restart on every slide. See
[what the manifest records](qa.md#what-the-manifest-records).

Reach for it when a deck has been hand-edited after its build — see the "don't rebuild
after a hand-edit" rule in [`docs/pptx-deck-building.md`](pptx-deck-building.md).

A file that will not open as a `.pptx` — corrupt, truncated, or another Office app's
format under a renamed extension — is refused with a message naming the path, not a
traceback.

## `conform` — onboard a brand template

```bash
bin/run conform templates/brand.pptx --adopt brand
```

Derives a theme from the template, drives every capability through it one slide at a
time, and reports what it carries. Exits non-zero if any exercise failed. Full doc:
[`docs/conform.md`](conform.md).

| Flag | Effect |
|---|---|
| `--out` / `-o` | Output root. Default `out/conform/`. |
| `--adopt` | Keep the derived theme as `templates/<NAME>.theme.yaml`, with a copy of the template in `templates/`. Refuses an existing name. |
| `--force` | With `--adopt`, replace an existing theme of that name. |

`out/` is disposable by design, so a theme left there is a theme you will lose. `--adopt`
is what moves it somewhere durable: after it, `templates/<NAME>.theme.yaml` is the file to
read and edit, and any deck can name it as `theme: <NAME>`.

## `shot` — screenshot an HTML file

```bash
bin/run shot card.html --width 900
```

Renders an HTML file to a PNG with headless Chrome, cropped to content. This is the same
path the `panel` and `document` components use internally; the command exposes it for
building and eyeballing a card's HTML before wiring it into a deck.

| Flag | Effect |
|---|---|
| `--out` / `-o` | Output `.png`. Default: alongside the `.html`. |
| `--width` / `-w` | Layout width in CSS px. Default 1000. |
| `--scale` | Device scale factor. Default 2, or `$PPTXKIT_SHOT_SCALE`. |

See [`docs/panels.md`](panels.md) for the CSS-variable contract these cards are themed
through, and the canvas ceiling that clips a too-tall one.

## `sample` — a template to onboard against

```bash
bin/run sample
bin/run conform templates/sample.pptx --adopt sample
```

Writes a small brand template pptxkit owns outright, so the `conform` walkthrough runs
with nothing to hunt for. It lands in the theme directory — `templates/` unless
`PPTXKIT_THEME_DIR` says otherwise — because `--adopt` reads a template where it lives
and refuses one anywhere else. Pass a path to override; if that path is outside the
theme directory, the printed next step tells you to move it there first.

| Flag | Effect |
|---|---|
| `--force` | Replace an existing file at that path. Without it, an existing file is an error — you may have put your own there. |

It carries a real colour scheme (six accents, none of them Microsoft's, so a derived
theme binds all six and a hued `dk2` becomes `inverse`), a font scheme in a face
pptxkit can measure, and slides whose runs use it — because `conform` takes the face
from a template's own slides, so an unmeasured face here would reach every deck built
from the adopted theme.

**It is a pipeline fixture, not brand-variance evidence.** It is shaped like what the
compiler already handles, so a clean `conform` against it proves the pipeline runs —
never that pptxkit copes with a template nobody designed against. That question is
only answered by real brand templates in `templates/`, and the sample is stamped in
its `docProps` so [the corpus guard](testing.md) refuses it mechanically rather than
by convention.

## `doctor` — what this install can do

```bash
bin/run doctor
```

```
PASS   glyphs.bundle     4,001 glyphs @ 50f0603134ce
PASS   theme.builtin     base resolves (packaged)
WARN   tools.soffice     not found (soffice) — needed by render, and QA's
                         render-based checks; brew install --cask libreoffice
SKIP   templates.brands  no brand template — tests/test_templates.py skips, so a green suite is
                         the unit tests only
```

Read-only ground truth, in pf-core's `pf-doctor` shape (run that one too — it attests
the framework install). Reports the version that answered, the glyph bundle against its
manifest, whether `theme: base` resolves and from where, the sample template, the
corpus, and each of the four external tools **resolved exactly as the runtime resolves
them, then checked for existence** — so a `PPTXKIT_SOFFICE` or `PPTXKIT_CHROME` pointing
somewhere wrong shows up here rather than mid-render.

**A missing tool is a `WARN`, never a `FAIL`.** LibreOffice, Poppler and Chrome are
each needed by some commands and irrelevant to others, so absence is a fact about this
machine; every warning names the command that installs it. Only a broken install —
a glyph bundle that does not match its manifest — fails, and only that sets a non-zero
exit.

## `glyphs` — the built-in icon set

```bash
bin/run glyphs verify
bin/run glyphs sync --ref 50f0603134ce7b70b2d71b686cc13e8b57ccb74c
```

The ~4,000 Material Symbols that `icon:` draws from ship as one archive,
`glyphs.zip`, beside the `glyphs.sum` manifest that pins them and the set's licence.
Four thousand loose files cost more in per-file overhead than in content — as one
stored archive they are 716KB in the wheel against 16.5MB installed as files, and a
glyph reads faster because there is nothing to decompress.

| Sub-command | Flag | Effect |
|---|---|---|
| `verify` | | Check every glyph in the bundle against its manifest hash. Offline, and what `bin/setup` runs. |
| `sync` | | Rebuild the bundle from the upstream commit the manifest already pins — repairs a checkout without moving the set. |
| `sync` | `--ref` | Vendor a **different** upstream commit: fetch, curate, and rewrite both files. |

**Updating to newer icons is `sync --ref` and reading a text diff.** The fetch is a
blobless sparse checkout of just the icon selection (~119MB, ~35s, into a temp
directory that is deleted straight after), then three rules are applied — the
`_fill1_24px` suffix comes off the name, a missing `viewBox` is inserted, and any
drawing that only reads right under nonzero winding is dropped, because pptxkit fills
every glyph even-odd. The command prints what moved:

```
vendored the set @ 7c1e9ab04d3f (118 dropped — they need nonzero winding)
  added      14  cardiology, chess, deceased, dew_point, …
  changed     3  groups, language, pin_drop
```

Then `git diff` on `glyphs.sum` names every icon that appeared, vanished or was
redrawn — one line each, so **a re-vendor is reviewed as text, never as a binary**.
Run `bin/test` after: the suite re-measures the winding property over whatever the
sync produced, and fails naming any glyph that cannot ship. Provenance and the full
curation rules are in `src/pptxkit/icons/glyphs/material/SOURCE.md`.

## Environment variables

Every knob is read from `os.environ` **at call time**, so `.env` changes take effect
between invocations without a reinstall. Entry points load `.env` from the working
directory on startup. Defaults live beside the code that reads them, not here.

| Variable | Governs |
|---|---|
| `PPTXKIT_THEME_DIR` | Where a spec's `theme:` name is resolved — `<name>.theme.yaml`, beside the `.pptx` it binds to. Relative to the CWD, so set it when running from outside the repo. A name not found there falls back to the packaged built-ins, so `theme: base` resolves anywhere. |
| `PPTXKIT_CACHE_DIR` | Cache root — rendered panel PNGs and media extracted from templates. |
| `PPTXKIT_ICON_DIR` | A glyph directory searched *before* the theme's own and the shipped set. |
| `PPTXKIT_SOFFICE` | The LibreOffice command `render` invokes. |
| `PPTXKIT_PDFTOPPM` | The Poppler `pdftoppm` command that rasterizes the converted PDF. |
| `PPTXKIT_RENDER_DPI` | Rasterization DPI for `render`. |
| `PPTXKIT_CHROME` | The Chrome/Chromium/Edge binary for `shot` and panels. Autodetected when unset. |
| `PPTXKIT_SHOT_SCALE` | Device scale factor for HTML screenshots. |
| `PPTXKIT_CHROME_NO_SANDBOX` | Set to `1` to pass `--no-sandbox`. Off by default: a card renders HTML that may not be yours, and the sandbox is the process-level boundary around it — what the HTML itself may do is bounded separately by the content policy in `SECURITY.md`. Needed in containers that deny the unprivileged user namespace Chrome needs; implied when running as root, where the sandbox cannot work at all. A build that dies for want of a sandbox names this variable. |
| `PPTXKIT_SHOT_TIMEOUT_S` | How long to wait on headless Chrome. |
| `PPTXKIT_SHOT_CANVAS_H` | Render canvas height in CSS px. A taller card is clipped by the browser; the build detects that and tells you to raise this. |
| `PPTXKIT_PDFTOTEXT` | The `pdftotext` command QA's text extraction uses. |
| `PPTXKIT_PDFTOTEXT_TIMEOUT_S` | Timeout for it. |

pf-core supplies the rest — `LOG_LEVEL`, `LOG_FILE` and the API-key vars. See
`docs/pf-core/config.md` (the symlink `bin/setup` creates).

## External tools

Four commands shell out. A tool that is not installed fails with a message naming the
binary it looked for, the command that installs it here, and the `PPTXKIT_*` knob that
points at one installed elsewhere:

| Tool | Needed by |
|---|---|
| LibreOffice (`soffice`) | `render`; QA's render-based checks |
| Poppler `pdftoppm` | `render`; QA's render-based checks |
| Poppler `pdftotext` | QA's overflow check |
| Chrome / Chromium / Edge | `shot`; **building** any deck that uses a `document` component |

`inspect` and `qa --no-render` need none of them. `build` needs only Chrome, and only when
the spec uses `document:` — the one component rendered through HTML. `panel:` paints a
native rectangle and needs nothing external, despite the name it shares with
[`panels.md`](panels.md).

## Exit codes and logging

`0` on success. `1` for a domain failure — a bad spec, a template that cannot yield a
theme, a `--fail-on` threshold met, or a `conform` run with any failure. Unexpected
errors exit non-zero with a traceback in the log.

A missing or failing external tool exits 1 with its message and no traceback: the fix
is on the machine, not in the stack. Debug logging is `-v` / `--verbose` — see
[Global options](#global-options).

## Adding a command

1. Add a `@app.command()` function in `src/pptxkit/cli.py`. Keep it thin: parse
   arguments, call **one** service or orchestrator function, print the result. No
   business logic: the command parses arguments and calls one function.
2. Raise the project's own errors (`SpecError`, `ThemeError`, `LayoutError`) for bad
   input; pf-core's CLI scaffold maps them to exit codes and messages already.
3. Add the command to this doc's table of contents and give it a section.
4. If it introduces an env knob, follow the wrapper-function recipe in
   `compile/build.py`'s `theme_dir()` — a module constant for the default, a
   wrapper calling `pf_core.utils.env.resolve_*` so a malformed value warns and falls
   back rather than crashing, and the read happening at call time — then add it to
   `.env.example` **and** the table above.
