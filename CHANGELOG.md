# Changelog

Notable changes to pptxkit, newest first. The project is pre-1.0 — pin to a tagged
release; `main` is the development line.

## v0.1.0 — 2026-08-29

Initial public release.

- Python 3.12+, on pf-core 0.21.
- `pptxkit build` compiles a declarative `.deck.yaml` against a theme into a branded
  `.pptx`, a build manifest, and a `.content.md` of the deck's words.
- Twenty-two slide components, 29 native chart kinds, imagery with fit/crop and scrim
  solving, HTML panels rendered through headless Chrome, and animation — builds,
  click-to-reveal and slide transitions.
- The built-in `base` theme ships inside the package, so `theme: base` resolves with no
  checkout. A file of the same name in `PPTXKIT_THEME_DIR` takes precedence.
- Default faces are Helvetica and Courier New, which resolve to metric clones in
  Keynote, PowerPoint and LibreOffice alike.
- `pptxkit conform <template>.pptx --adopt <name>` derives a theme from a brand template
  and drives every capability through it.
- `pptxkit sample` writes a small brand template to conform against, so the walkthrough
  needs no brand file. It lands in the theme directory, where `--adopt` can read it.
- `pptxkit qa` checks geometry bounds, reserved regions, WCAG contrast, minimum font
  size and render-based overflow against a built deck's manifest.
- `render` and `qa` write into `render/<deck>/` beside the deck, so two decks in one
  directory never overwrite each other's slides.
- A built deck carries only the slide layouts it uses; `build --keep-layouts` retains
  the rest, and the media only they reach.
- Speaker notes declare their notes master on the presentation, which Keynote requires
  to open the file.
- `pptxkit doctor` reports the version, the glyph bundle, theme resolution and the
  external tools, naming the install command for anything missing. `--version` prints
  it on its own.
- An absent external tool names the binary, the `PPTXKIT_*` variable that overrides it
  and the install command for the platform; `qa` also names `--no-render`, which runs
  every check that needs no tool.
- ~4,000 Material Symbols ship as one archive; `pptxkit glyphs verify` checks it against
  its manifest and `pptxkit glyphs sync` re-vendors it from upstream — the one command
  that uses the network.
- Supporting commands: `render`, `shot`, `inspect`, `diff`, `new`, `demo`.
- One directory for a brand: `templates/` holds the `.pptx` and the theme derived
  from it, side by side. `theme: <name>` resolves `<name>.theme.yaml` there, and a
  theme names its template by bare filename — nothing is ever copied. A template is
  adopted where it lives; adopting one from elsewhere is refused.
- Re-running `conform --adopt` on the same template is a refresh that keeps hand
  edits; `--force` re-derives and discards them.
- The suite's primary guard drives every template in that directory
  (`tests/test_templates.py`, `PPTXKIT_TEMPLATES_MIN` to require a minimum).
- Headless Chrome runs sandboxed. `PPTXKIT_CHROME_NO_SANDBOX=1` passes
  `--no-sandbox`, which is implied when running as root.
- Every rendered card carries a content policy: no frames, objects or embeds, no
  script but pptxkit's own height probe, and images and fonts from `data:`/`http(s):`
  only. A `file://` URL in card markdown no longer renders a local file into the deck.
- Importing `pptxkit` no longer touches the root logger; handlers land on the
  `pptxkit` logger, and an application that configured logging first keeps its own.
- All text is read and written as UTF-8 regardless of the platform locale.
- Every XML part of a `.pptx` is parsed with entity expansion and network access
  refused, so a package from someone else cannot amplify or forge through a DTD.
- The sdist ships a runnable suite: `tests/`, `docs/` and `examples/` travel with
  it, and brand templates and derived brand themes are excluded from both dists.
