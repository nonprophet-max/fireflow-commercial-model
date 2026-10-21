---
name: fireflow-client-journey
description: Research a prospective FireFlow client (a bank or other organisation that has approached Persistent Labs) and build a proposed commercial journey deck for it under its real name. Also builds fictional, publicly shareable examples such as Falaj Community Bank.
---

# FireFlow client journey

Use this skill when an organisation approaches Persistent Labs and we want to show it how FireFlow would be introduced in its case. The skill turns research about that organisation into a proposed commercial journey under its real name. The output is a guided deck of up to 15 screens in the visual system of the standard walkthrough. It covers the organisation's context, three initial agents, systems to connect, why FireFlow (a standard screen of platform features), the five deployment stages with timings, inference costs at full volume, possible add-on services and estimated year-one FireFlow fees.

The same generator also builds **fictional examples** for public use, where the real organisation must not be recognisable. `clients/falaj.json` (Falaj Community Bank) is the reference example of that mode.

| | Real client proposal (normal case) | Fictional public example |
| --- | --- | --- |
| `"fictional"` in the client file | `false` | `true` |
| Name in the deck | The organisation's real name | A placeholder name, labelled fictional |
| Research facts | Used directly; public sources only, recorded in `sources` | Generalised so the real entity can't be identified |
| Output folder | `proposals/<slug>/index.html` | `examples/<slug>/index.html` |
| Labels in the deck | "Proposal for <client>", "Proposal for discussion · estimated figures" | "Illustrative example · fictional bank" |

The standard walkthrough (`index.html`, `overview.html`, `detailed.html` and the PDF at the repository root) stays separate. Nothing in it links to proposals or examples.

## Rules

1. **Public information only, and accurate.** Use what the organisation publishes and reputable press. Record every source URL in `sources` (kept in the client file, not shown in the deck). Don't state anything you couldn't source as a fact about the client. Volumes, token counts and rates are estimates and are labelled as such.
2. **Client logo: official files only, for decks addressed to that client.** The deck stays in FireFlow style. By default the client card shows the real name with a neutral monogram. To show the client's logo instead, set `client.logo` (and, if they have one, `client.logo_dark` for dark backgrounds). Rules:
   - Use the official file only: one the client sent us, or one from their official press or media kit. Never redraw, trace or screenshot a logo.
   - Follow the client's brand guidelines (clear space, colours, minimum size). If you're unsure, ask the client contact first; they usually send the right file at the same time.
   - A deck with the client's logo is for that client only. Showing it to anyone else (website, case studies, other prospects) needs the client's explicit permission.
   - Fictional examples never use a logo. The build refuses one.
   - Logo files live next to the client file, e.g. `clients/logos/<slug>.svg`, and are as confidential as the proposal.
3. **Standard terms come from `commercial-terms.json`.** Don't type fees or rates into a client file. When the standard model changes, edit that file and rebuild every proposal and example.
4. **On-premises and client control, never vendor access.** FireFlow runs in the client's own data centre or private cloud. The client's engineers connect its systems and decide what each agent may do. Persistent Labs works with synthetic data in staging and has no access to the client's systems, bank data or customer data. Never write that Persistent Labs connects to, reads or operates client systems; say who on the client side does it. By default the private model also runs inside the client's infrastructure (`rates.private.hosting: "self-hosted"`), so the surcharge uses a market-rate reference and nothing is re-billed.
5. **Model policy.** UIO (customer-facing) agents use private models only. BPO agents may use frontier models for non-sensitive tasks. The build refuses a UIO agent on a frontier model.
6. **Exactly three initial agents.** Stage 1 scopes the first three agents. Other agents are optional add-on services, with no prices ("quoted separately").
7. **Confidentiality.** A real proposal names a prospect and its plans. Commit `clients/<slug>.json` and `proposals/<slug>/` only to a private repository, and confirm the repository is private before pushing. Don't publish proposals on a public site.
8. **Fictional examples only:** derive, don't copy. Keep the type of organisation, city, segments, channels and pain points. Remove or generalise anything that identifies the real entity: product names, partners, vendors, branch locations, executives, unusual products. Its research notes and real names stay out of the repository.

## Steps

1. **Research the organisation** (web search). Cover:
   - home city, regulator, licence type and age;
   - segments and approximate size;
   - channels: app, contact centre, branches, partners;
   - onboarding (in the UAE: UAE Pass, Emirates ID);
   - main products;
   - technology platform and vendors, if public;
   - recent news and strategy, including AI plans;
   - public pain points: app-store and review sites, press.

   Keep a source URL for every fact you will use.
2. **Frame the problem and choose three initial agents.** Lead with value, not basic support. The thesis (PersistentAI Overview): customers use a bank app only to pay, while their attention and spend go to marketplaces and other apps; UIO brings many apps into one end-to-end journey inside the client's app, which the client owns. Good initial agents create engagement or revenue: a shopping concierge (agentic commerce with partner merchants), a money co-pilot (bills, subscriptions, savings within customer-set limits) and life-event journeys (one request runs a whole chain of services). Internal BPO agents (KYC, credit, compliance) usually fit better as add-ons. A plain support chatbot should not be the headline. Then pick up to four add-ons. For each agent, estimate the monthly volume and the tokens per unit, including every model call in the flow.
3. **Write the client file.** Copy `clients/_template.json` to `clients/<slug>.json`, then fill every `TODO`. If the client has provided its logo, save it to `clients/logos/` and set `client.logo`. `reference/client-format.md` describes each field. Keep copy short: every screen must fit a phone without scrolling. The build refuses a file that still contains `TODO`. Fill the two story screens too: `before_after` (one customer journey today versus in the client's app) and `team` (the client's product team builds its own agents in the visual builder, tested in staging).
4. **Build** from the repository root:

   ```sh
   python3 skills/fireflow-client-journey/build_journey.py \
     skills/fireflow-client-journey/clients/<slug>.json proposals/<slug>/index.html \
     --forbid /path/other-client-names.txt
   ```

   The build validates the file, calculates the figures, writes one self-contained HTML file and prints the numbers it used. `--forbid` is optional for real proposals: list other clients' names to catch copy-paste mistakes. For a fictional example it is required in practice: list the real entity's names and identifiers, and keep that list outside the repository.
5. **Check.**
   - Arithmetic: recompute the printed figures by hand once (see "Calculations").
   - Facts: each statement about the client matches a source in `sources`.
   - Layout: open the deck at desktop and phone sizes, in light and dark themes. No text may overlap, clip or need page scrolling. If a screen is too dense, shorten its copy.
   - Tone: direct and operational. No compliance guarantees, no performance claims, no criticism of the client.
   - Access: nothing says or implies that Persistent Labs reaches the client's systems or data.
   - Links: every "Learn more" link opens.
6. **Deliver.** The deck is a single HTML file that can be sent to the client as is, or hosted privately. Commit the client file and the deck on a branch and open a pull request.

## Calculations

- Agent inference per month = units × tokens in ÷ 1,000,000 × input rate + units × tokens out ÷ 1,000,000 × output rate.
- Surcharge = inference × 25% (private) or 4% (frontier).
- Ramp: zero before the limited-rollout month, then the `ramp` shares in the client file, then 100%.
- Maintenance in year one = prepayment + monthly fee × the number of months from the later of go-live and the end of the prepaid months, up to month 12.
- Year-one FireFlow fees = Stage 1 fee + maintenance + surcharge. This is the figure on the last screen, so its three cards add up to it.
- Inference itself is shown separately ("Plus ~$X inference at cost"). Either the client pays the model provider directly or Persistent Labs passes it through at cost; either way it is not a FireFlow fee. Add-on services are excluded.

## Files

| File | Purpose |
| --- | --- |
| `build_journey.py` | Generator, validation, calculation and name check (Python 3.9+, standard library). |
| `commercial-terms.json` | Standard FireFlow terms used by every deck. |
| `platform.json` | Standard "Why FireFlow" screen: five platform features (policies, on-premises, sandboxes, no-code builder, API and MCP integration). Keep it in line with docs.persistentai.org; update it when the platform changes. |
| `links.json` | Standard "Learn more" links for each screen: persistentai.org, the FireFlow docs and blog, and sections of the detailed commercial plan. Update it when those pages move. |
| `clients/_template.json` | Starting point for a real client proposal. |
| `clients/falaj.json` | Fictional reference example (Falaj Community Bank). |
| `reference/client-format.md` | Field-by-field description of a client file. |
| `assets/` | Deck styles, navigation script, icons and bundled Red Hat fonts (SIL OFL). Copied from the standard walkthrough; update them together. |
