# Wellfound (formerly AngelList Talent)

Sites change; treat this as what usually happens and confirm with `sgaj look`.

## Before applying

Wellfound applies with the user's Wellfound profile, not a per-job form. Check once that the profile has a resume, current role, experience, skills, location preferences and a salary expectation. If it doesn't, help the user complete it (in their tab, from `profile.md` facts) before applying.

## Search

Start at `https://wellfound.com/jobs` and set role, location, remote and salary filters in the page. Job cards show salary and equity ranges, which helps the fit check. Collect postings with `sgaj links --match /jobs/` (posting URLs look like `https://wellfound.com/jobs/<id>-<slug>`) and track those URLs.

## Applying

- **Apply** opens a panel asking for a short note to the hiring team. This note is the application: 3 to 5 sentences, specific to the company and role, grounded in the user's real experience. No generic cover-letter filler.
- Some postings add screening questions or ask for availability and salary; answer from the profile.
- Submitting usually turns the button into **Applied**. Confirm with `sgaj look` before tracking.
- Many startups list a salary range: skip roles clearly below the profile's minimum.
