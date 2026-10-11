# Applying to one job

## Before the form

- `sgaj track has URL`: if it prints `yes`, skip the job.
- `sgaj read` the job description. Decide fit against `profile.md`. Hard stops: below the pay minimum when pay is posted, work authorization the user does not have, location they excluded. Record skips with `--status skipped --notes "<reason>"` so they are not reconsidered.
- Note two or three requirements from the description that the user genuinely matches. Use them for free-text answers ("Why this company", cover letters).

## Reading `look`

```
[12] textbox "First name *" = "" (required)
[15] select "Years of experience *" = "Select…" options: 0-1 | 1-2 | 2-4 | 5+
[18] radio "No" in "Will you require visa sponsorship? *" (off)
[21] combobox "Notice period *" = "Select..." (required)
[24] file "Resume/CV *" = "(none)"
[30] button "Submit application"
alerts: Please complete all required fields
captcha: recaptcha (ask the user to solve it in the browser)
```

- `textbox` or `searchbox`: `fill`. Location, school, company and other autocompletes: `pick` (it types, waits for suggestions and clicks the best match).
- `select`: `select N OPTION` with an option from the list.
- `combobox` that is not a text field: `pick N TEXT`, which opens it and clicks the matching option.
- `radio`: click the option whose `in "<question>"` matches. `checkbox`: click only to change its state.
- `file`: `upload N ~/job-hunt/resume/<file>`. Never click upload buttons; `sgaj` refuses because they open a dialog it cannot control.
- Off-screen fields are listed too. Acting on them scrolls automatically.
- `frame (cross-origin …)`: the form is embedded from another site. `sgaj goto` that URL and fill it there.

## Filling a step

Answer every visible field, then send one batch:

```bash
sgaj do '[["fill",12,"Simarpreet"],["fill",13,"Singh"],["pick",14,"Lucknow"],["select",15,"1-2"],
          ["click",18],["upload",24,"C:/Users/me/job-hunt/resume/resume.pdf"]]'
```

For long free text, pass the JSON on stdin with `sgaj do -` to avoid shell-quoting trouble. A batch stops at the first error and prints a fresh `look`. Fix the failing field and continue with the remaining ones; do not resend fields that already succeeded.

Then click Next/Continue (it can be the last action of the batch) and repeat for the next step.

## Answers

- Use `profile.md` facts word for word for contact details, links, dates and numbers.
- Years of experience: use the profile's number; for ranges pick the bucket containing it.
- Pay: when the posting has a range, answer within it but never below the minimum. Otherwise use the target. Match the field's unit (annual, monthly, LPA).
- Free text (why us, cover letter): 2 to 4 honest sentences tied to the job description and the user's real experience. No buzzword padding.
- Yes/no eligibility questions you cannot answer from the profile: ask the user. Never guess.

## Before submitting

1. `sgaj check`. Fix everything listed under `missing required:` and any `alerts:`.
2. Captcha: `sgaj show`, ask the user to solve it, wait for them, then `sgaj check` again.
3. Approval (unless `auto_submit: yes`), for example:
   > Ready to submit: **Acme AI, AI Engineer** (Lever), resume `resume.pdf`. Sponsorship: No. Notice: 30 days. Expected pay: 18 LPA. Submit?
4. On yes: click Submit. Then `sgaj read` and look for a confirmation ("Application submitted", "Thanks for applying"). If you see errors instead, fix them and ask again before resubmitting.

## After

- Success: `sgaj track add "<Company>" "<Role>" "<job URL>" "<Platform>" --notes "<resume used, anything notable>"`.
- Stopped for the user (login, unclear question): `--status needs-user` with the reason, so it can be resumed later.
- Close extra tabs you opened. Wait 30 to 90 seconds before the next application on LinkedIn or Indeed.
