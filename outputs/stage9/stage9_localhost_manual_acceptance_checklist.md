# Stage 9 Step 7A — Human Browser Acceptance Checklist

## Document control

- Tested branch: `phase8-public-demo-source`
- Tested commit: `7b877ae1448423f8c7e402af7ee2455f5973d0a7`
- Manual status: `PASS`
- Manual review performed: `true`
- Manual pass claimed: `true`
- Revision 1 automated coverage: one canonical Basic Form AppTest submission and rendered governance disclosures
- Reviewer name or initials: ____________________
- Review date: ____________________
- Browser and version: ____________________
- Operating system: ____________________
- Screen size or viewport: ____________________
- Localhost URL: ____________________
- Start time: ____________________
- End time: ____________________

## Start and stop

From the repository root, with the validated project environment active, run:

```bash
python -m streamlit run app/streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 \
  --server.headless true
```

Open `http://localhost:8501`. If the port is occupied, use the localhost URL printed by Streamlit. Do not bind to a public interface or use a tunnel. Stop the app with `Ctrl+C`.

## Startup and access

- [ ] Localhost URL opens — `PENDING_HUMAN_REVIEW`
- [ ] No browser security warning appears — `PENDING_HUMAN_REVIEW`
- [ ] Initial load completes without traceback or missing-artifact text — `PENDING_HUMAN_REVIEW`
- [ ] Loading behavior is understandable — `PENDING_HUMAN_REVIEW`
- [ ] Browser refresh returns to a safe initial state — `PENDING_HUMAN_REVIEW`

## Six pages

For each page, confirm it opens, its title is visible, layout is readable, text is not clipped, controls do not overlap, normal desktop width has no severe overflow, and no local path is shown.

- [ ] Overview — `PENDING_HUMAN_REVIEW`
- [ ] Contract Readiness — `PENDING_HUMAN_REVIEW`
- [ ] Demo Input Modes — `PENDING_HUMAN_REVIEW`
- [ ] Payload Builder & Preview — `PENDING_HUMAN_REVIEW`
- [ ] Safe Demo Inference — `PENDING_HUMAN_REVIEW`
- [ ] Governance & Limitations — `PENDING_HUMAN_REVIEW`

## Basic Form

- [ ] Basic Form is the default public mode — `PENDING_HUMAN_REVIEW`
- [ ] Field labels and help text are understandable — `PENDING_HUMAN_REVIEW`
- [ ] No personal identity or free-text field appears — `PENDING_HUMAN_REVIEW`
- [ ] Acknowledgement initially remains false — `PENDING_HUMAN_REVIEW`
- [ ] No inference occurs before explicit submission — `PENDING_HUMAN_REVIEW`
- [ ] Invalid input feedback is readable and safe — `PENDING_HUMAN_REVIEW`
- [ ] Valid fictional inference succeeds with non-decision framing — `PENDING_HUMAN_REVIEW`
- [ ] Required disclosures remain visible near the result — `PENDING_HUMAN_REVIEW`

Safe fictional example from committed vector `REQUEST_STANDARD_36`:

| Public field | Fictional value |
|---|---:|
| Fictional annual income | 65000 |
| Debt-to-income ratio (%) | 18.27 |
| Fictional home ownership | MORTGAGE |
| Fictional requested loan amount | 12000 |
| Fictional loan purpose | other |
| Fictional term | 36 months |
| Synthetic completion profile | SP_LOW_RISK_SIGNAL |

Select the required acknowledgement only after reading it, then submit explicitly.

## Sample Profiles

- [ ] All five fictional profiles are selectable — `PENDING_HUMAN_REVIEW`
- [ ] Profile descriptions are understandable — `PENDING_HUMAN_REVIEW`
- [ ] Switching profiles updates the interface without stale results — `PENDING_HUMAN_REVIEW`
- [ ] Acknowledgement behavior is understandable where applicable — `PENDING_HUMAN_REVIEW`
- [ ] `SP_LOW_RISK_SIGNAL` completes one fictional smoke inference — `PENDING_HUMAN_REVIEW`
- [ ] Result framing remains non-decision — `PENDING_HUMAN_REVIEW`

## Advanced Editor — Technical Mode

- [ ] Technical-mode warning is visible — `PENDING_HUMAN_REVIEW`
- [ ] The 49-feature interface is usable — `PENDING_HUMAN_REVIEW`
- [ ] Locked and derived features are visually distinguishable — `PENDING_HUMAN_REVIEW`
- [ ] `is_60_month` is read-only — `PENDING_HUMAN_REVIEW`
- [ ] Acknowledgement initially remains false — `PENDING_HUMAN_REVIEW`
- [ ] No automatic inference occurs — `PENDING_HUMAN_REVIEW`
- [ ] One canonical reset inference succeeds with safe framing — `PENDING_HUMAN_REVIEW`

Reset sequence:

1. Select `SP_LOW_RISK_SIGNAL`.
2. Change the allowed `dti` field to another valid value.
3. Select the acknowledgement, but do not submit.
4. Switch to `SP_MEDIUM_RISK_SIGNAL`.
5. Confirm the edit disappears, medium values load, `term_months = 60`, `is_60_month = 1`, acknowledgement is false, and no result appears.
6. Switch back to `SP_LOW_RISK_SIGNAL`.
7. Confirm low-profile values return, `term_months = 36`, `is_60_month = 0`, acknowledgement is false, and no previous result appears.

- [ ] Full reset sequence behaves as described — `PENDING_HUMAN_REVIEW`

## Governance, privacy, and result framing

- [ ] Fictional portfolio-demo limitation is visible — `PENDING_HUMAN_REVIEW`
- [ ] Non-lending-decision statement is visible — `PENDING_HUMAN_REVIEW`
- [ ] Production-use warning is visible — `PENDING_HUMAN_REVIEW`
- [ ] Fairness limitation is visible — `PENDING_HUMAN_REVIEW`
- [ ] Legal limitation is visible — `PENDING_HUMAN_REVIEW`
- [ ] No approval, rejection, eligibility, or underwriting recommendation appears — `PENDING_HUMAN_REVIEW`
- [ ] No name, national ID, address, bank account, email, or phone field appears — `PENDING_HUMAN_REVIEW`
- [ ] No free-text, file-upload, or camera input appears — `PENDING_HUMAN_REVIEW`

## Desktop and narrow-screen usability

- [ ] Buttons are visible and clearly labelled — `PENDING_HUMAN_REVIEW`
- [ ] Tables fit or scroll understandably — `PENDING_HUMAN_REVIEW`
- [ ] Form controls do not overlap — `PENDING_HUMAN_REVIEW`
- [ ] Captions, disclosures, and result cards remain readable — `PENDING_HUMAN_REVIEW`
- [ ] Sidebar navigation remains usable — `PENDING_HUMAN_REVIEW`
- [ ] At a reduced width, primary content remains readable — `PENDING_HUMAN_REVIEW`
- [ ] At a reduced width, no critical button or disclosure becomes inaccessible — `PENDING_HUMAN_REVIEW`
- [ ] At a reduced width, no severe horizontal overflow appears — `PENDING_HUMAN_REVIEW`

This narrow-screen check is a basic portfolio usability review, not formal mobile certification.

## Optional sanitized screenshots

Optional screenshots may cover the overview, Basic Form before submission, a safe result, Sample Profile selection, Advanced Editor reset, and Governance & Limitations. Exclude personal information, terminal usernames, local paths, browser account details, credentials, and complete canonical payloads.

## Human decision

- Blocking issue count: ____________________
- Non-blocking note count: ____________________
- Reviewer notes: ____________________
- Recommended next action: ____________________

Select exactly one only after completing every check:

- [x] `PASS`
- [ ] `PASS_WITH_NON_BLOCKING_UI_NOTES`
- [ ] `FAIL_BLOCKING_LOCALHOST_ISSUE`

Human acceptance decision: `PASS`
