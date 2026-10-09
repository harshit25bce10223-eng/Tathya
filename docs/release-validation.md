# Validation and remaining release limits

## Completed and checked

- Full isolated PostgreSQL backend suite: **239 passed, zero skipped**. The application database was not used for tests.
- Frontend TypeScript and production build passed.
- Mobile TypeScript, Expo lint and SDK dependency compatibility checks passed. Android/iOS Hermes and web bundles exported. These exports are not device certification or a signed APK.
- A real document trial ran from the browser: candidate audit `acaefa9d-2c2c-4e48-b3b3-96c2cd136d91` completed. Its INR 50 lakh claim contradicted the copied INR 41.6 lakh source, matching the reviewer label. Original source versions remained intact.
- A live 12-case synthetic component evaluation exposed and then verified the Gemini nullable JSON-schema fix. The judge arm matched all expected statuses; deterministic rules alone detected 3 of 8 authored risks. This small smoke set does not establish production accuracy.
- Mobile browser verification displayed a valid signature and history while withholding the stale passport score. The empty conditional text rendering warning was corrected. Upload now includes a file-order confirmation with an explicit primary-document choice.
- Production template secrets are rejected; Docker build context excludes secrets, uploads and runtime caches. Dedicated Compose YAML parsed successfully, and its frozen frontend workspace package install passed in an isolated directory.

## Not complete or not checked here

- Actual hosting, HTTPS certificate issuance, image build and restart/backup recovery: no Docker executable or authenticated server/domain is available. See `deploy/README.md` for the concrete release candidate and checks.
- Signed Android/iOS release and physical-device camera, OCR, QR, SecureStore and permission checks: Expo account/signing access and device tooling are unavailable. Foreground local completion alerts are implemented; background push delivery is not.
- Mobile dependency security (verified 2026-10-10): `npm audit` reports **18 high advisories** across Expo CLI/Metro, React Native, Reanimated/Worklets, `braces` and `node-forge`. A non-forced `npm audit fix --dry-run` reported zero package changes; the forced suggestion downgrades Expo to 44 and React Native to 0.72, so neither was applied. GitHub currently lists no patched versions for the `braces` stack-exhaustion advisory or the `node-forge` signature-verification advisory. Expo SDK 58 is still beta (its release notes say the beta runs three to four weeks), so this project remains on stable SDK 57. Do not treat the mobile dependency tree as security-certified or publish a store release until maintained upstream fixes are available and the updated tree passes the mobile checks.
- OpenAI fallback credentials have exhausted credits. Configured Gemini worked after the schema repair. If providers become unavailable, inconclusive checks must stay uncertain.
- A large unseen, independently labelled benchmark, production model calibration and full category/policy ablations remain outside the synthetic smoke evaluation. Z3 proves the submitted typed constraints; it does not establish source authority.
- The entire existing Playwright suite was not run in this final validation. Browser checks above exercised the live trial and mobile public verification; they do not certify every account/UI journey.

Evidence is saved locally under `artifacts/system-repair-validation/`: `backend-tests.log`, `evaluation-live.json`, `mobile-audit.json` and `release-summary.json`. Runtime files, credentials and model data are excluded from the source commit.
