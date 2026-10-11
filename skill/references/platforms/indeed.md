# Indeed

Sites change; treat this as what usually happens and confirm with `sgaj look`.

## Search

Use the country site (`in.indeed.com`, `uk.indeed.com`, `www.indeed.com`, …):

```
https://in.indeed.com/jobs?q=AI+engineer&l=Remote&fromage=7&sort=date
```

| Parameter | Meaning |
|---|---|
| `q`, `l` | what and where (`Remote` works as a location) |
| `fromage` | posted within N days (`1`, `3`, `7`, `14`) |
| `sort=date` | newest first |

Collect postings with `sgaj links --match jk=`. Open each as `https://in.indeed.com/viewjob?jk=<id>` and track that URL.

## Applying

- **Apply now** (Indeed Apply) runs a multi-step flow, often on `smartapply.indeed.com`: contact info, resume (Indeed resume or uploaded file; prefer the user's file), employer questions, sometimes a "relevant experience" step (job title and company from the resume), then review and **Submit your application**.
- **Apply on company site** sends the user to the employer's site: follow `ats.md` there.
- Indeed often shows a Cloudflare check. When `look` reports a captcha or a "verify you are human" page: `sgaj show`, ask the user to complete it, then continue.

## Cautions

Indeed prohibits automated access in its terms. Pace applications and keep volumes modest.
