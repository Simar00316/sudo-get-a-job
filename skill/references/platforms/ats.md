# Company career sites (applicant tracking systems)

Most "Apply on company site" links land on one of these. Recognise them by URL. Sites change; treat this as what usually happens and confirm with `sgaj look`.

## Greenhouse

`job-boards.greenhouse.io/<company>/jobs/<id>` or `boards.greenhouse.io/...`

- The form is on the same page as the description, below it. The **Apply** button only scrolls there; `look` already lists the fields.
- Resume: `upload`. Some forms also offer "Enter manually"; prefer the upload.
- Custom questions and a voluntary self-identification (EEO) section follow; EEO answers come from the profile, default "Decline to self-identify".
- On a company's own careers page, Greenhouse is often embedded in an iframe: `look` shows `frame (cross-origin …) https://job-boards.greenhouse.io/embed/job_app?...`. Run `sgaj goto` with that URL and fill it there.

## Lever

`jobs.lever.co/<company>/<id>` (form at `/apply`)

- Uploading the resume triggers parsing ("Analyzing resume…") that may overwrite name, email or phone. `sgaj wait 3`, then `look` and correct any field that differs from the profile.
- Current location is an autocomplete: `pick`.
- Questions sit in plain lists without fieldsets; `look` shows their question text after `in`.
- An hCaptcha may appear on submit: `sgaj show` and ask the user.

## Ashby

`jobs.ashbyhq.com/<company>/<id>/application`

- The upload control is a button over a hidden input: `upload` the button's number.
- Yes/No questions are often rendered as buttons; click the one for the answer and confirm with `look`.
- Location fields are autocompletes: `pick`.

## Workday

`<company>.wd<N>.myworkdayjobs.com/...`

- Every company needs its own Workday account, which needs a password. Stop and hand the tab to the user (`sgaj show`) to create the account or sign in. Never choose a password yourself.
- After sign-in, "Autofill with Resume" can prefill steps; still review every field against the profile.
- Steps: My Information, My Experience, Application Questions, Voluntary Disclosures, Self Identify, Review. Dropdowns are button lists: `pick`. Date fields may need the format shown in their placeholder.
- Workday is slow: `sgaj wait 2` after each Save and Continue before `look`.

## SmartRecruiters, iCIMS, Taleo, others

Use the generic flow from `apply.md`. Expect account creation on iCIMS and Taleo; hand those to the user like Workday.
