# LinkedIn

Sites change; treat this as what usually happens and confirm with `sgaj look`.

## Search

Build the URL instead of clicking through filters:

```
https://www.linkedin.com/jobs/search/?keywords=AI%20Engineer&location=India&f_AL=true&f_TPR=r604800&f_WT=2
```

| Parameter | Meaning |
|---|---|
| `keywords`, `location` | free text |
| `f_AL=true` | Easy Apply only (apply inside LinkedIn) |
| `f_TPR` | posted within: `r86400` day, `r604800` week, `r2592000` month |
| `f_WT` | `1` onsite, `2` remote, `3` hybrid (comma-separate several) |
| `f_E` | experience: `1` internship, `2` entry, `3` associate, `4` mid-senior, `5` director |
| `sortBy=DD` | newest first |

Collect postings with `sgaj links --match /jobs/view/`. The results list loads more as it scrolls: `sgaj scroll down` then `links` again. Open each posting as `https://www.linkedin.com/jobs/view/<id>/` and track that URL.

## Applying

- **Easy Apply** opens a modal with several steps: contact info (usually prefilled; check phone and email), resume (choose an existing one or `upload`), additional questions, then **Review** and **Submit application**.
- Additional questions are often "How many years of experience do you have with X?" as numeric text fields. Enter whole numbers from the profile. If the user has none, enter 0 rather than inventing.
- The review step usually has a **Follow <company>** checkbox ticked by default. Untick it unless the user wants to follow companies.
- After submitting, a confirmation dialog appears; close it with **Done** or **Dismiss**.
- **Apply** (without "Easy") opens the company's own site, usually in a new tab: `sgaj tabs`, `sgaj attach <company or ATS name>`, then follow `ats.md`.
- "Save" (bookmark) is not applying; ignore it.

## Cautions

LinkedIn restricts automated activity. Keep a human-like pace (30 to 90 seconds between applications), stay well under the user's daily limit, and stop immediately if LinkedIn shows a warning, a security check or a sign-in prompt; hand the tab to the user with `sgaj show`.
