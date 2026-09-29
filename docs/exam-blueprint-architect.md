# dbt Architect Certification — Official Blueprint

Transcribed from the **official dbt Labs study guide**, "dbt Architect Certification Exam
Study Guide **V.6.4**".

- Exam guide: <https://www.getdbt.com/certifications/dbt-architect-certification-exam>
- Study guide PDF: <https://www.getdbt.com/dbt-assets/dbt-certificate-study-guide-for-cloud-architect>

[accessed 2026-09-29]

---

## Logistics (published)

| Item | Value |
|---|---|
| Duration | 2 hours |
| Format | Online proctored |
| **Length** | **65 questions** |
| **Passing score** | **65% or higher** — reported immediately |
| Price | $200 (each retake also $200) |
| Language | English, Japanese, French |
| Expiration | 2 years after award |
| Browsers | Caveon Web browsers |
| Recommended | SQL proficiency and 6+ months administrating an **Enterprise** dbt account |

Note the prerequisite difference from the AE exam: this one assumes **Enterprise account
administration** experience, not just dbt usage.

### Scope statement

> "Assesses your ability to design secure, scalable dbt implementations, with a focus on
> environment orchestration, role-based access control, integrations with other tools,
> and collaborative development workflows aligned with best practices."

### Scoring

Identical wording to the AE guide: 1 point per correct answer, 0 for incorrect, all
questions weighted equally, plus an undisclosed number of unscored research questions.

### Still NOT published

Per-topic weighting; how many of the 65 questions fall in each topic; how many are
unscored.

---

## Question formats

The same six as the AE exam. See [question-formats.md](question-formats.md).

---

## Topic Outline (official)

> "The dbt Architect Certification Exam has been designed to assess the following topics
> and sub-topics."

### Topic 1 — Configuring dbt data warehouse connections → `arch-01`

| Task | Sub-topic (verbatim) |
|---|---|
| 1.1 | Understanding how to connect the warehouse |
| 1.2 | Configuring IP whitelist |
| 1.3 | Creating and testing a connection for the project |
| 1.4 | Authenticating through OAuth to access the data in dbt |
| 1.5 | Adding Client ID and Secret for OAuth |

### Topic 2 — Configuring dbt git connections → `arch-02`

| Task | Sub-topic |
|---|---|
| 2.1 | Connecting the git repo to dbt |
| 2.2 | Setting up integrations with git providers |

### Topic 3 — Creating and maintaining dbt environments → `arch-03`

| Task | Sub-topic |
|---|---|
| 3.1 | Understanding access control to different environments |
| 3.2 | Determining when to use a service account |
| 3.3 | Rotating key pair authentication via the API |
| 3.4 | Understanding environment variables |
| 3.5 | Creating a new dbt deployment environment |
| 3.6 | Setting a default schema/dataset for environments |
| 3.7 | Understanding custom branches and how to configure them to environments |
| 3.8 | Configuring dbt to allow deferral to other environments |

### Topic 4 — Creating and maintaining job definitions → `arch-04`

| Task | Sub-topic |
|---|---|
| 4.1 | Set up a CI job with deferral |
| 4.2 | Understanding steps within a dbt job |
| 4.3 | Scheduling a job to run on schedule |
| 4.4 | Implementing run commands in the correct order |
| 4.5 | Creating a new dbt job |
| 4.6 | Configuring optional settings such as environment variable overrides, threads, deferral, target name, and dbt version override |
| 4.7 | Generating documentation on a job that populates the dbt Catalog page |
| 4.8 | Configuring jobs to be triggered after other dbt jobs (job chaining) |
| 4.9 | Configuring Advanced CI |
| 4.10 | Configuring self-deferral |
| 4.11 | Understanding when to use which type of job deferral |

### Topic 5 — Configuring dbt security and licenses → `arch-05`

| Task | Sub-topic |
|---|---|
| 5.1 | Creating service tokens for API access |
| 5.2 | Assigning permission sets |
| 5.3 | Creating license mappings |
| 5.4 | Adding and removing users |
| 5.5 | Adding SSO application for dbt Enterprise |
| 5.6 | Creating and assigning RBAC |

### Topic 6 — Setting up monitoring and alerting for jobs → `arch-06`

| Task | Sub-topic |
|---|---|
| 6.1 | Setting up email notifications |
| 6.2 | Using Webhooks for event-driven integrations with other systems |

### Topic 7 — Setting up a dbt mesh and leveraging cross-project references → `arch-07`

| Task | Sub-topic |
|---|---|
| 7.1 | Setting up additional dbt projects |
| 7.2 | Understanding how environment types relate to cross-project references |
| 7.3 | Utilizing model governance |

### Topic 8 — Configuring and using dbt Catalog → `arch-08`

| Task | Sub-topic |
|---|---|
| 8.1 | Using dbt Catalog to understand the current lineage, troubleshoot issues and optimize cost and performance |
| 8.2 | Using dbt Catalog to find public models and cross-project references |

---

## Sub-topic share — a proxy, not a weight

| Domain | Sub-topics | Share | ~Questions of 65 |
|---|---|---|---|
| `arch-04` Creating and maintaining job definitions | 11 | 28.2% | ~18 |
| `arch-03` Creating and maintaining dbt environments | 8 | 20.5% | ~13 |
| `arch-05` Configuring dbt security and licenses | 6 | 15.4% | ~10 |
| `arch-01` Configuring dbt data warehouse connections | 5 | 12.8% | ~8 |
| `arch-07` Setting up a dbt mesh and cross-project references | 3 | 7.7% | ~5 |
| `arch-02` Configuring dbt git connections | 2 | 5.1% | ~3 |
| `arch-06` Setting up monitoring and alerting for jobs | 2 | 5.1% | ~3 |
| `arch-08` Configuring and using dbt Catalog | 2 | 5.1% | ~3 |

> **Derived proxy for study-time allocation only.** Not an official weight.

The conclusion that matters: **jobs and environments together are roughly half the
enumerated surface**, and deferral appears in *four* separate sub-topics (3.8, 4.1, 4.10,
4.11). If you learn one thing deeply for this exam, make it deferral.

---

## Notable scope signals

- **Deferral is the single most-repeated concept** — environment deferral, CI deferral,
  self-deferral, and "when to use which type" are four distinct sub-topics.
- **OAuth appears twice** (1.4, 1.5) and the first official sample question is about why
  SSO-based connections are wrong for staging/production deployment environments. The
  answer turns on token expiry, which is why service accounts exist (3.2).
- **Key pair rotation via the API** (3.3) is oddly specific — it will be tested.
- **Advanced CI and job chaining** get their own sub-topics (4.9, 4.8).
- **dbt Catalog replaced older docs surfaces** — note 4.7 says a docs job "populates the
  dbt Catalog page". Naming drift here is a live version-drift trap.

---

## Overlap with the AE track

`arch-07` (Mesh, cross-project refs, model governance) overlaps with AE's `ae-02`
(contracts, versions, constraints). Split them by perspective:

- **`ae-02`** — the model author declaring a contract or a version on their own model.
- **`arch-07`** — the platform architect wiring projects together and deciding what is
  `public`.

Write the shared concept note once in the track whose depth it belongs to and cross-link;
`build_topic_index.py` resolves `` `note.md` `` references across tracks.
