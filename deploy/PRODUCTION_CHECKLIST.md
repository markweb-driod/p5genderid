# FaceClass production release checklist

## Required release artifacts

- [ ] An appropriately licensed, consent-aware dataset is documented.
- [ ] Subject-disjoint train, validation and test splits are frozen.
- [ ] `backend/ml/models/model.keras` is present and loads successfully.
- [ ] `metadata.json` and `evaluation.json` contain verified test metrics.
- [ ] Subgroup and image-quality performance has been reviewed.
- [ ] The deployed model version is registered in `model_versions`.

## Configuration and security

- [ ] `.env.production` was created from `.env.production.example` and is excluded from Git.
- [ ] Database, Flask and JWT secrets are independently generated.
- [ ] `MOCK_MODE=false` and the startup readiness check passes.
- [ ] HTTPS terminates at the reverse proxy or trusted edge.
- [ ] Only ports 80/443 are public; MySQL and Redis remain private.
- [ ] Database backups are encrypted and a restore has been rehearsed.
- [ ] Retention, deletion, privacy notice and incident-response procedures are documented.

## Verification

- [ ] Registration, authentication, authorization and account recovery pass.
- [ ] User records cannot be accessed by another user.
- [ ] Admin endpoints reject ordinary users.
- [ ] Invalid, malformed, oversized, no-face and multiple-face uploads are rejected.
- [ ] Model failure never creates a prediction record.
- [ ] Upload and camera flows pass on desktop and mobile browsers.
- [ ] Accessibility and keyboard navigation pass.
- [ ] Load, dependency, vulnerability and backup/restore tests pass.
