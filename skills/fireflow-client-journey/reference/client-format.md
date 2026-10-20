# Client file format

A client file is JSON. For a real client, start from `clients/_template.json`; for a fictional example, start from `clients/falaj.json`. Keep copy short: every screen must fit a phone without scrolling. The build refuses any value that still contains `TODO`.

## Top level

| Field | Required | Meaning |
| --- | --- | --- |
| `slug` | yes | Folder name for the output, e.g. `acme-bank`. |
| `fictional` | yes | `false` for a real client proposal, `true` for a fictional public example. |
| `client` | yes | The organisation (below). |
| `sources` | real clients | Public source URLs behind every fact used. Internal: not shown in the deck. |
| `links` | no | `standard_model` and `overview` URLs. When present, the deck links to the standard walkthrough. Use relative links only for decks hosted next to it (as `examples/falaj` is). Omit them for a file sent to a client. |
| `rates` | yes | Reference market rates in $ per million tokens: `private` and `frontier`, each with `in`, `out` and a short `label`. These are estimates, not quotes. |
| `timeline` | yes | Month numbers (below). |
| `agents` | yes | All agents: exactly three with `"initial": true`, the rest are add-ons. |
| `addons_extra` | no | One sentence about further add-ons without volume figures. |
| `slides` | yes | Screen copy (below). |

## `client`

- `name`: full name, as the organisation writes it (real client) or the placeholder name (fictional).
- `short`: short form used in copy and the header ("Proposal for SHORT").
- `facts`: three short lines for the client card: type and city, segments and approximate size, channels and languages.
- `proposal_note` (real clients, optional): replaces the default sentence on the title screen ("Based on public information about … final fees and scope are agreed in the contract.").
- `fictional_note` (fictional only, required): one sentence saying the organisation is fictional.
- `logo` (real clients, optional): path to the client's official logo, relative to the client file, e.g. `logos/acme.svg`. SVG, PNG, JPG or WebP, up to 500 KB; SVGs with scripts are refused. It replaces the monogram on the title screen. With only one version, the logo sits on a white plate in the dark theme so it stays legible.
- `logo_dark` (optional): a version for dark backgrounds. When present, each theme shows its own version and no plate is used.
- `brand` (optional): `color_light` and `color_dark` (hex) for the client card's accent, plus `tagline`. Mainly for fictional examples. For real clients, leave it out and the FireFlow accent is used.

## `timeline`

- `setup_month`: Stage 1 invoice (normally 1).
- `prepay_month`: maintenance prepayment, invoiced at Stage 2.
- `limited_month`: Stage 4 limited rollout; the surcharge starts here.
- `go_live_month`: Stage 5 full production.
- `year_months`: length of the year-one view (normally 12).
- `ramp`: share of full volume by month before 100%, e.g. `{"6": 0.05, "7": 0.5}`.

Stage copy in `slides.*.eyebrow` names weeks or months. Keep it consistent with these numbers.

## `agents[]`

| Field | Meaning |
| --- | --- |
| `id` | Short identifier. |
| `name` | Display name. |
| `workload` | `UIO` (customer-facing) or `BPO` (internal). |
| `model` | `private` or `frontier`. UIO must be `private`. |
| `initial` | `true` for the three Stage 1 agents. |
| `unit` | What is counted: chats, sessions, cases, documents. |
| `units_per_month` | Estimated volume at full run-rate. |
| `tokens_in`, `tokens_out` | Tokens per unit, including all model calls in the flow. |
| `desc` | One line: what the agent does. |
| `control` | Initial agents only: what the agent may not do alone (Stage 3 screen). |

## `slides`

Each screen has `eyebrow`, `title` (two parts: a plain line and an emphasised line) and `lead`. Some screens take more:

- `bank.items` and `systems.items`: three `{icon, title, text}` entries. Icons: `message`, `check`, `activity`, `layers`, `shield`, `connect`, `launch`, `scope`, `code`, `branch`.
- `bank.gate`, `systems.gate`, `staging.gate`, `build.gate`, `prepare.gate`, `rollout.gate`: `[LABEL, sentence]`.
- `staging.note`: `[title, text]` under the Stage 1 price.
- `build.steps`, `rollout.steps`: three `[title, text]` pairs.
- `operate.split`: two `[who, responsibilities]` pairs.
- `usage.gate`: the label is replaced by "ASSUMED RATES", and the sentence is appended to the rate note.

The title-screen and last-screen notices depend on `fictional` and are generated. Figures (fees, prepayment, monthly start, surcharge, totals) are calculated: don't write them into copy.
