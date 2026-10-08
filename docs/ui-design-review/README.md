# Tathya Phase 1 + Phase 2 UI review

Status: ready for design review; design approved by the user; approved for publication to main. Release branch: `codex/ui-approved-release`. Only frontend and design review files are included; backend, mobile and legacy root application files remain unchanged.

## Page coverage

| Surface | Pages and behaviours |
| --- | --- |
| Authentication | Login, signup, password recovery/reset; shared responsive layout, input validation and password visibility |
| Brand splash | Original logo with nine component reveals, golden orbit, soft glow, Hindi tagline; 2.6 seconds once per tab session, reduced-motion support and replay preview at `/splash` |
| Submit | File blocks, picker/drop, supported-format and 50 MB validation, duplicate prevention, remove files, real multipart request |
| Results | One score/context page, deductions, findings, versions, public verification link, processing refresh and failure state |
| Control | Dashboard, searchable/filterable audit archive, queue and investigator with reviewer access gate |
| Investigation | Finding explanation, structured JSON, version/location/hash references; required decision note and explicit score recalculation |
| Sources & truth | Audit selector, document search, current/previous version, canonical hash and empty/error states |
| Trust policies | Read-only description of current scoring and reviewer safeguards |
| Metrics & drift | Actual loaded audit counts and volume for latest seven active days, grouped in India time |
| Governance & admin | Existing user management APIs, superuser gate, desktop table, mobile account cards, create/edit/delete controls |
| Settings | Profile, password, account deletion tabs |
| Public verification | No authentication required; issued score, document hash, signature and chain results; missing/invalid/malformed states |
| Common states | Loading, no records, no matches, unavailable service, generic error, branded 404; production developer panels hidden |

## Backend boundaries

The UI uses existing service contracts. Custom policy editing, independent score sub-metrics, source authority assignment, original evidence text and historical score drift are not exposed by the current API. These gaps are explicitly shown rather than populated with invented results. Account management preserves existing superuser restrictions; the template account form does not edit reviewer roles. Production records are never seeded by the design review.

Screenshots and browser tests use clearly labelled Preview records. Real authentication, database storage, full audit processing and live authorization still require an integrated backend run. The public verifier does not expose an audit ID or document owner.

Mobile companion work is deferred and preserved at `artifacts/deferred-mobile`; it is excluded from this web change.

## Validation

TypeScript, production build and authored-file Biome checks passed. Browser checks cover multipart file contents, drag/drop, validation, navigation, search/filter, review notes, saved decisions, rescore, processing completion refresh, responsive layouts, reviewer access, empty/API/malformed states, all auth pages, governance dialogs, settings tabs and public proof states. Splash checks cover first visit, session persistence, replay and reduced motion. No page errors were observed.

Run against production preview on port 4173 from the repository root:

```text
node frontend/tests/design-review/review.cjs
node frontend/tests/design-review/pages.cjs
node frontend/tests/design-review/splash.cjs
node frontend/tests/design-review/preserved.cjs
```

## References

[Linear dashboard context](https://linear.app/now/dashboards-best-practices), [Notion upload blocks](https://www.notion.com/help/images-files-and-media), [Vercel analytics](https://vercel.com/docs/analytics), [Attio structured output](https://attio.com/engineering/blog/ask-attio-a-technical-look-at-our-new-agent), [community Linear spacing reference](https://github.com/Khalidabdi1/design-ai/blob/main/design-md/linear/DESIGN.md). Patterns were adapted to existing components and real data contracts.

[Open the screenshot gallery](GALLERY.md).

## Preservation check

The existing Items route and navigation remain available. Its existing create, edit and delete service calls and forms are retained; presentation and accessible menu labels were refreshed. The frontend explicitly uses its Tailwind Vite pipeline without loading the legacy root app PostCSS configuration. No backend or mobile code is included in this release.
