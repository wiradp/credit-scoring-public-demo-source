# Stage 9 — Controlled Public Deployment Checklist

## Current Handoff Identity

- Current HEAD: `06579e72522bc23dc830d49612e8fb20b01a1970`
- Current tracked repository files: 105
- Controlled deployment release-candidate scope: 99 files
- The six additional tracked paths are historical deployment evidence or test-only files and are intentionally excluded from the controlled release candidate.
- Historical Step 6 and Stage 7A references below are retained as provenance and procedure, not as the current HEAD identity.

## A. Release Candidate Identity

- [ ] Confirm baseline `5051f614db66e2ead73a54795e1e5c087df5e197` and the human-audited Step 6 hashes.

## B. Source Repository Preconditions

- [ ] Confirm clean committed source and no unexpected deployment artifact.

## C. Required Branch and Commit

- Branch: `phase8-public-demo-source`
- [ ] Use only the current controlled-demo handoff commit after separate human authorization.

## D. Streamlit Entry Point

- Entry point: `app/streamlit_app.py`

## E. Python and Dependency Selection

- Dependency file: `requirements.txt`
- Tested Python: 3.10.12
- [ ] Review direct pins and hosted-runtime Python selection.

## F. Runtime Artifact Availability

- [ ] Verify every runtime path and hash in the release-candidate manifest.

## G. Secrets Configuration

- Secrets required: none
- [ ] Do not add a secrets file or credential prompt.

## H. Public Privacy Review

- [ ] Confirm no identity, free-text, document, image, or real-customer fields and no input or payload logging.

## I. Governance Disclosure Review

- [ ] Confirm fictional portfolio-demo, non-decision, non-production, fairness, and legal limitations remain visible.

## J. Streamlit Cloud Setup Fields

- Branch: `phase8-public-demo-source`
- Entry point: `app/streamlit_app.py`
- Secrets: none
- Repository URL: supply only after separate authorization.
- Public app URL: not available; deployment has not occurred.

## K. First Deployment Verification

- [ ] App starts.
- [ ] All pages render.
- [ ] Basic Form is default.
- [ ] Sample Profiles are available.
- [ ] Advanced Editor is available.
- [ ] Acknowledgements are false.
- [ ] No automatic inference occurs.
- [ ] One successful fictional inference runs per mode.
- [ ] Required disclosure is visible.
- [ ] No personal fields, secret prompt, or traceback appears.

## L. Three-Mode Public Smoke

- [ ] Recheck Sample Profile, Basic Form, and Advanced Editor using fictional values only.

## M. Failure and Rollback Procedure

- [ ] Stop if hashes, imports, startup, privacy, or scope differ.
- [ ] Disable only a separately authorized hosted release; never bypass fail-closed guards.

## N. Post-Deployment Evidence to Capture

- [ ] Record commit, settings, UTC time, sanitized smoke summary, and URL only after deployment.
- [ ] Never capture raw inputs, complete payloads, credentials, or personal information.

## O. Deployment Authorization Gate

Do not deploy until the current controlled-demo handoff and its 99-file release candidate have passed human audit, Git scope review, staging audit, commit, and post-commit audit.

Current public deployment authorization: **false**. This checklist performs no release action.
