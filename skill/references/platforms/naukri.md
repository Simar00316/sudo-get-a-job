# Naukri (India)

Sites change; treat this as what usually happens and confirm with `sgaj look`.

## Before applying

Naukri applies with the user's Naukri profile and resume. Check that the uploaded resume, key skills, current CTC, expected CTC and notice period match `profile.md`; recruiters filter on them.

## Search

```
https://www.naukri.com/ai-engineer-jobs-in-bengaluru?experience=1&jobAge=7
```

The path encodes keywords and location (`<keywords>-jobs-in-<city>`, or `<keywords>-jobs` for anywhere). `experience` is years and `jobAge` is days since posting. Collect postings with `sgaj links --match job-listings` and track those URLs.

## Applying

- **Apply** on Naukri itself is often one click. Some postings then open a side drawer of recruiter questions in a chat-like format: answer each one from the profile, one at a time, using `look` after each answer.
- **Apply on company site** goes to the employer's site: follow `ats.md`.
- Confirm the success message ("Applied", "You have successfully applied") before tracking.
