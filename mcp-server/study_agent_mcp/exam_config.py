"""Single source of truth for exam metadata. Nothing else may hardcode a domain.

TRACKS
------
  `ae`   — dbt Analytics Engineering Certification Exam
  `arch` — dbt Architect Certification Exam

PROVENANCE — this is an OFFICIAL outline, not a derived one
-----------------------------------------------------------
Domains and tasks below are transcribed from the official dbt Labs study guides:

  AE:   "dbt Analytics Engineering Certification Exam Study Guide", updated for
        dbt Core 1.11 — 7 numbered topics with their sub-topics.
        https://www.getdbt.com/dbt-assets/certifications/dbt-certificate-study-guide-version-1-11
  ARCH: "dbt Architect Certification Exam Study Guide V.6.4" — 8 numbered topics.
        https://www.getdbt.com/dbt-assets/dbt-certificate-study-guide-for-cloud-architect

Each domain is one official Topic. Each task is one official sub-topic bullet, with its
title quoted from the guide. Keywords are ours (for classification); titles are dbt Labs'.

WEIGHTS ARE STILL NOT PUBLISHED
-------------------------------
Both guides state only: "The exam is scored on a point basis, with 1 point for each
correct answer, and 0 points for incorrect answers. All questions are weighted equally."
Neither publishes how many of the 65 questions fall in each topic.

So `weight` remains None. The honest proxy is **sub-topic count** — AE Topic 1 has 14
sub-topics while Topic 4 has 2 — and because coverage targets are flat per task, that
proxy falls out of the task counts automatically. `subtopic_share()` surfaces it
explicitly, labelled as a derived proxy.
"""
from __future__ import annotations

from typing import Optional

# --------------------------------------------------------------------------- #
# Exam-level facts. Every one is stated in the official study guide.
# --------------------------------------------------------------------------- #

EXAM_FACTS = {
    "ae": {
        "id": "ae",
        "code": "DBTAE",
        "name": "dbt Analytics Engineering Certification Exam",
        "duration_minutes": 120,
        "question_count": 65,
        "passing_score_pct": 65,
        "cost_usd": 200,
        "delivery": "online proctored",
        "validity_years": 2,
        "languages": ["English", "Japanese"],
        "target_version": "dbt Core 1.11",
        "guide_version": "updated for dbt Core 1.11",
        "recommended_experience": "SQL proficiency and 6+ months of dbt experience",
        "weights_published": False,
        "exam_guide_url": "https://www.getdbt.com/certifications/analytics-engineer-certification-exam",
        "study_guide_url": "https://www.getdbt.com/dbt-assets/certifications/dbt-certificate-study-guide-version-1-11",
        "official_url": "https://www.getdbt.com/dbt-certification",
        "scope_statement": (
            "Evaluates your ability to build, test, and maintain models to make data "
            "accessible to others, and to use dbt to apply engineering principles to "
            "analytics infrastructure."
        ),
    },
    "arch": {
        "id": "arch",
        "code": "DBTARCH",
        "name": "dbt Architect Certification Exam",
        "duration_minutes": 120,
        "question_count": 65,
        "passing_score_pct": 65,
        "cost_usd": 200,
        "delivery": "online proctored",
        "validity_years": 2,
        "languages": ["English", "Japanese", "French"],
        "target_version": None,
        "guide_version": "V.6.4",
        "recommended_experience": (
            "SQL proficiency and at least six months administrating an Enterprise "
            "dbt account"),
        "weights_published": False,
        "exam_guide_url": "https://www.getdbt.com/certifications/dbt-architect-certification-exam",
        "study_guide_url": "https://www.getdbt.com/dbt-assets/dbt-certificate-study-guide-for-cloud-architect",
        "official_url": "https://www.getdbt.com/dbt-certification",
        "scope_statement": (
            "Assesses your ability to design secure, scalable dbt implementations, with "
            "a focus on environment orchestration, role-based access control, "
            "integrations with other tools, and collaborative development workflows "
            "aligned with best practices."
        ),
    },
}

DEFAULT_TRACK = "ae"

# Both guides: "An undisclosed number of unscored questions will be included on each
# exam. These are unmarked and indistinguishable from scored questions."
UNSCORED_QUESTIONS_NOTE = (
    "An undisclosed number of unscored research questions are mixed in and are "
    "indistinguishable from scored ones, so not all 65 questions count toward the score."
)


# --------------------------------------------------------------------------- #
# Domains == official Topics. Task titles are quoted from the study guides.
# --------------------------------------------------------------------------- #

DOMAINS: dict[str, dict] = {
    # ============================ Analytics Engineering ===================== #
    "ae-01": {
        "track": "ae",
        "dir": "01-developing-and-optimizing-models",
        "title": "Developing and optimizing dbt models",
        "weight": None,
        "provenance": "AE study guide, Topic 01 (14 sub-topics)",
        "tasks": {
            "1.1": ("Identifying and verifying any raw object dependencies", [
                "source(", "{{ source", "sources.yml", "raw table", "raw object",
                "dependency", "dependencies", "upstream", "hard coded",
                "hardcoded table", "database + schema",
            ]),
            "1.2": ("Understanding core dbt materializations", [
                "materialization", "materialized", "view", "table", "ephemeral",
                "materialized_view", "cte", "create table as", "create view as",
                "rebuilt", "persisting",
            ]),
            "1.3": ("Conceptualizing modularity and how to incorporate DRY principles", [
                "modularity", "dry", "refactor", "reusable", "staging", "intermediate",
                "mart", "jinja", "macro", "{% macro", "duplication", "common logic",
                "project structure",
            ]),
            "1.4": ("Using commands such as build, run, test, docs, show, snapshot, and seed", [
                "dbt build", "dbt run", "dbt test", "dbt docs", "dbt show",
                "dbt snapshot", "dbt seed", "dbt compile", "--select", "--exclude",
                "node selection", "graph operator", "dbt docs generate",
            ]),
            "1.5": ("Creating a logical flow of models and building clean DAGs", [
                "dag", "ref(", "{{ ref", "lineage", "build order", "downstream",
                "model flow", "runs after", "execution order", "build in the correct order",
            ]),
            "1.6": ("Defining configurations in dbt_project.yml", [
                "dbt_project.yml", "+materialized", "config-version", "model-paths",
                "seed-paths", "macro-paths", "vars", "project config", "folder config",
                "+tags", "+schema",
            ]),
            "1.7": ("Using dbt Packages", [
                "package", "packages.yml", "dbt deps", "dbt_utils", "dbt-utils",
                "dbt_expectations", "codegen", "audit_helper", "hub.getdbt.com",
                "revision", "install package",
            ]),
            "1.8": ("Creating Python Models", [
                "python model", "dbt.ref", "def model(dbt, session)", "pandas",
                "pyspark", "snowpark", "dataframe", ".py model",
            ]),
            "1.9": ('Providing access to users to models with the "grants" config', [
                "grants", "grant select", "privileges", "copy_grants",
                "database_role", "revoke", "access to users",
            ]),
            "1.10": ("Creating snapshots in YAML", [
                "snapshot", "snapshots.yml", "slowly changing", "scd", "check strategy",
                "timestamp strategy", "unique_key", "updated_at", "check_cols",
                "invalidate_hard_deletes", "dbt_valid_from", "dbt_valid_to",
            ]),
            "1.11": ("Selecting the optimal incremental strategy based on a dataset's characteristics", [
                "incremental", "is_incremental", "incremental_strategy", "merge",
                "append", "delete+insert", "insert_overwrite", "on_schema_change",
                "--full-refresh", "new records", "only new data",
            ]),
            "1.12": ("Validating model logic and schema definitions in dry-runs using the --empty flag", [
                "--empty", "empty flag", "dry run", "dry-run", "zero rows",
                "validate schema", "build --empty",
            ]),
            "1.13": ("Running models in sample mode using the --sample flag", [
                "--sample", "sample mode", "sample flag", "subset of data",
            ]),
            "1.14": ("Understanding advanced dbt materializations such as microbatch", [
                "microbatch", "batch_size", "event_time", "lookback", "begin",
                "backfill", "partitioned batch",
            ]),
        },
    },
    "ae-02": {
        "track": "ae",
        "dir": "02-model-governance",
        "title": "Managing dbt models governance",
        "weight": None,
        "provenance": "AE study guide, Topic 02 (3 sub-topics)",
        "tasks": {
            "2.1": ("Adding contracts to models to ensure the shape of models", [
                "contract", "enforced: true", "model contract", "shape of models",
                "data_type", "column type", "contract enforcement",
            ]),
            "2.2": ("Creating different versions of our models and deprecating the old ones", [
                "model version", "versions:", "latest_version", "deprecation_date",
                "deprecate", "defined_in", "include/exclude",
            ]),
            "2.3": ("Defining constraints in YAML to enforce data integrity at the platform level", [
                "constraint", "constraints:", "check constraint", "primary key",
                "foreign key", "data integrity", "platform level", "warn_unenforced",
            ]),
        },
    },
    "ae-03": {
        "track": "ae",
        "dir": "03-debugging-modeling-errors",
        "title": "Debugging data modeling errors",
        "weight": None,
        "provenance": "AE study guide, Topic 03 (5 sub-topics)",
        "tasks": {
            "3.1": ("Understanding logged error messages", [
                "error message", "logs/dbt.log", "stack trace", "compilation error",
                "database error", "runtime error", "parsing error", "log output",
            ]),
            "3.2": ("Troubleshooting using compiled code", [
                "compiled code", "target/compiled", "target/run", "dbt compile",
                "compiled sql", "rendered sql",
            ]),
            "3.3": ("Troubleshooting .yml compilation errors", [
                "yml", "yaml error", "indentation", "invalid configuration",
                "properties file", "schema.yml", "yaml compilation",
            ]),
            "3.4": ("Developing and implementing a fix and testing it prior to merging", [
                "feature branch", "pull request", "git pull", "git fetch",
                "before merging", "code review", "head branch", "merge conflict",
            ]),
            "3.5": ("Managing dbt behavior with flags", [
                "flags", "global config", "behavior change", "--fail-fast",
                "--warn-error", "--no-partial-parse", "flags:", "behavior flag",
            ]),
        },
    },
    "ae-04": {
        "track": "ae",
        "dir": "04-troubleshooting-pipelines",
        "title": "Troubleshooting and optimizing dbt pipelines",
        "weight": None,
        "provenance": "AE study guide, Topic 04 (2 sub-topics)",
        "tasks": {
            "4.1": ("Troubleshooting and managing failure points in the DAG", [
                "failure point", "skipped", "downstream model", "blocked",
                "dag failure", "partial failure", "fail-fast", "test-before-model",
                "skip relation",
            ]),
            "4.2": ("Using dbt clone", [
                "dbt clone", "zero-copy", "cloned relation",
            ]),
        },
    },
    "ae-05": {
        "track": "ae",
        "dir": "05-implementing-tests",
        "title": "Implementing dbt tests",
        "weight": None,
        "provenance": "AE study guide, Topic 05 (3 sub-topics)",
        "tasks": {
            "5.1": ("Using generic, singular, custom, custom generic, and unit tests on a wide variety of models and sources", [
                "generic test", "singular test", "custom generic test", "unit test",
                "unit_tests:", "unique", "not_null", "accepted_values", "relationships",
                "data_tests:", "tests:", "given", "expect", "fixture", "mock input",
            ]),
            "5.2": ("Testing assumptions for dbt models and sources", [
                "assumption", "test a source", "source test", "data quality",
                "severity", "warn_if", "error_if", "store_failures", "where config",
                "threshold",
            ]),
            "5.3": ("Implementing various testing steps in the workflow", [
                "testing workflow", "test before", "ci test", "when to test",
                "test ordering", "test in the pipeline",
            ]),
        },
    },
    "ae-06": {
        "track": "ae",
        "dir": "06-external-dependencies",
        "title": "Implementing and maintaining external dependencies",
        "weight": None,
        "provenance": "AE study guide, Topic 06 (2 sub-topics)",
        "tasks": {
            "6.1": ("Implementing dbt exposures", [
                "exposure", "exposures:", "dashboard", "downstream consumer",
                "maturity", "exposure type", "depends_on",
            ]),
            "6.2": ("Implementing source freshness", [
                "source freshness", "dbt source freshness", "loaded_at_field",
                "freshness:", "warn_after", "error_after", "stale source",
            ]),
        },
    },
    "ae-07": {
        "track": "ae",
        "dir": "07-dbt-state",
        "title": "Leveraging the dbt state",
        "weight": None,
        "provenance": "AE study guide, Topic 07 (2 sub-topics)",
        "tasks": {
            "7.1": ("Understanding state and state selection", [
                "state:modified", "state:new", "--state", "defer", "--defer",
                "--favor-state", "manifest.json", "run_results.json", "artifact",
                "state selection", "slim ci",
            ]),
            "7.2": ("Using dbt retry", [
                "dbt retry", "rerun failed", "previous invocation", "resume",
            ]),
        },
    },

    # ================================= Architect ============================= #
    "arch-01": {
        "track": "arch",
        "dir": "01-warehouse-connections",
        "title": "Configuring dbt data warehouse connections",
        "weight": None,
        "provenance": "Architect study guide, Topic 1 (5 sub-topics)",
        "tasks": {
            "1.1": ("Understanding how to connect the warehouse", [
                "warehouse connection", "account-level connection", "snowflake",
                "databricks", "bigquery", "redshift", "connection settings",
                "extended attributes",
            ]),
            "1.2": ("Configuring IP whitelist", [
                "ip whitelist", "ip allowlist", "ip restriction", "allowlist",
                "static ip", "firewall", "network policy", "egress ip",
            ]),
            "1.3": ("Creating and testing a connection for the project", [
                "test connection", "project connection", "connection test",
                "connection credentials", "connection failure",
            ]),
            "1.4": ("Authenticating through OAuth to access the data in dbt", [
                "oauth", "development credentials", "access token", "token expire",
                "re-authorize", "sso-based connection", "identity provider",
            ]),
            "1.5": ("Adding Client ID and Secret for OAuth", [
                "client id", "client secret", "oauth app", "security integration",
                "redirect uri",
            ]),
        },
    },
    "arch-02": {
        "track": "arch",
        "dir": "02-git-connections",
        "title": "Configuring dbt git connections",
        "weight": None,
        "provenance": "Architect study guide, Topic 2 (2 sub-topics)",
        "tasks": {
            "2.1": ("Connecting the git repo to dbt", [
                "git repo", "repository", "deploy key", "git clone",
                "connect repository", "managed repository", "ssh key",
            ]),
            "2.2": ("Setting up integrations with git providers", [
                "github", "gitlab", "azure devops", "native integration",
                "git provider", "pull request", "merge request",
            ]),
        },
    },
    "arch-03": {
        "track": "arch",
        "dir": "03-environments",
        "title": "Creating and maintaining dbt environments",
        "weight": None,
        "provenance": "Architect study guide, Topic 3 (8 sub-topics)",
        "tasks": {
            "3.1": ("Understanding access control to different environments", [
                "environment access", "access control", "environment permission",
                "restrict environment",
            ]),
            "3.2": ("Determining when to use a service account", [
                "service account", "deployment credentials", "non-human",
                "production credentials", "automated deployment",
            ]),
            "3.3": ("Rotating key pair authentication via the API", [
                "key pair", "keypair", "rotate", "rotation", "private key",
                "admin api credentials",
            ]),
            "3.4": ("Understanding environment variables", [
                "environment variable", "env var", "env_var(", "dbt_env_secret",
                "variable override", "secret env var",
            ]),
            "3.5": ("Creating a new dbt deployment environment", [
                "deployment environment", "create environment", "environment type",
                "staging environment", "production environment",
                "development environment",
            ]),
            "3.6": ("Setting a default schema/dataset for environments", [
                "default schema", "custom schema", "dataset", "target schema",
                "generate_schema_name",
            ]),
            "3.7": ("Understanding custom branches and how to configure them to environments", [
                "custom branch", "main branch", "release branch",
                "branch per environment", "git branch setting",
            ]),
            "3.8": ("Configuring dbt to allow deferral to other environments", [
                "deferral", "defer to production", "defer to staging",
                "production environment ref",
            ]),
        },
    },
    "arch-04": {
        "track": "arch",
        "dir": "04-job-definitions",
        "title": "Creating and maintaining job definitions",
        "weight": None,
        "provenance": "Architect study guide, Topic 4 (11 sub-topics)",
        "tasks": {
            "4.1": ("Set up a CI job with deferral", [
                "ci job", "continuous integration", "pr job", "slim ci",
                "ci with deferral", "run on pull request",
            ]),
            "4.2": ("Understanding steps within a dbt job", [
                "job step", "run command", "job command", "steps within",
                "execution step",
            ]),
            "4.3": ("Scheduling a job to run on schedule", [
                "schedule", "cron", "scheduled job", "custom cron", "frequency",
            ]),
            "4.4": ("Implementing run commands in the correct order", [
                "command order", "correct order", "sequence of commands",
                "order of operations",
            ]),
            "4.5": ("Creating a new dbt job", [
                "create job", "new job", "deploy job", "job definition",
            ]),
            "4.6": ("Configuring optional settings such as environment variable overrides, threads, deferral, target name, and dbt version override", [
                "threads", "target name", "dbt version override", "override",
                "optional setting", "job setting", "concurrency",
            ]),
            "4.7": ("Generating documentation on a job that populates the dbt Catalog page", [
                "generate docs", "dbt docs generate", "documentation job",
                "populate catalog", "docs on a job",
            ]),
            "4.8": ("Configuring jobs to be triggered after other dbt jobs (job chaining)", [
                "job chaining", "triggered after", "upstream job", "chained job",
                "on job completion",
            ]),
            "4.9": ("Configuring Advanced CI", [
                "advanced ci", "compare changes", "data diff", "ci cache",
                "code change comparison",
            ]),
            "4.10": ("Configuring self-deferral", [
                "self deferral", "self-defer", "defer to itself",
                "previous run of this job",
            ]),
            "4.11": ("Understanding when to use which type of job deferral", [
                "type of deferral", "which deferral", "defer to environment",
                "defer to job", "deferral choice",
            ]),
        },
    },
    "arch-05": {
        "track": "arch",
        "dir": "05-security-and-licenses",
        "title": "Configuring dbt security and licenses",
        "weight": None,
        "provenance": "Architect study guide, Topic 5 (6 sub-topics)",
        "tasks": {
            "5.1": ("Creating service tokens for API access", [
                "service token", "api token", "token permission", "token scope",
                "administrative api", "discovery api", "semantic layer api",
            ]),
            "5.2": ("Assigning permission sets", [
                "permission set", "enterprise permission", "account admin",
                "job admin", "analyst", "developer permission",
                "project-level permission", "read-only",
            ]),
            "5.3": ("Creating license mappings", [
                "license", "license mapping", "developer license", "read-only license",
                "it license", "seat", "assign license",
            ]),
            "5.4": ("Adding and removing users", [
                "add user", "remove user", "invite", "deactivate", "user management",
                "seat management",
            ]),
            "5.5": ("Adding SSO application for dbt Enterprise", [
                "sso", "single sign-on", "saml", "okta", "azure ad", "entra",
                "google workspace", "scim", "enterprise sso",
            ]),
            "5.6": ("Creating and assigning RBAC", [
                "rbac", "role-based access", "user group", "group mapping",
                "assign role", "sso group",
            ]),
        },
    },
    "arch-06": {
        "track": "arch",
        "dir": "06-monitoring-and-alerting",
        "title": "Setting up monitoring and alerting for jobs",
        "weight": None,
        "provenance": "Architect study guide, Topic 6 (2 sub-topics)",
        "tasks": {
            "6.1": ("Setting up email notifications", [
                "email notification", "notification", "alert", "job outcome",
                "run status notification", "slack", "microsoft teams",
            ]),
            "6.2": ("Using Webhooks for event-driven integrations with other systems", [
                "webhook", "event-driven", "outbound", "http callback",
                "webhook subscription",
            ]),
        },
    },
    "arch-07": {
        "track": "arch",
        "dir": "07-mesh-and-cross-project",
        "title": "Setting up a dbt mesh and leveraging cross-project references",
        "weight": None,
        "provenance": "Architect study guide, Topic 7 (3 sub-topics)",
        "tasks": {
            "7.1": ("Setting up additional dbt projects", [
                "additional project", "multi-project", "dependencies.yml",
                "project dependency", "producer project", "consumer project",
            ]),
            "7.2": ("Understanding how environment types relate to cross-project references", [
                "cross-project", "cross project ref", "environment type",
                "public model ref", "staging environment ref",
            ]),
            "7.3": ("Utilizing model governance", [
                "model governance", "access:", "public", "protected", "private",
                "group:", "governed model",
            ]),
        },
    },
    "arch-08": {
        "track": "arch",
        "dir": "08-dbt-catalog",
        "title": "Configuring and using dbt Catalog",
        "weight": None,
        "provenance": "Architect study guide, Topic 8 (2 sub-topics)",
        "tasks": {
            "8.1": ("Using dbt Catalog to understand the current lineage, troubleshoot issues and optimize cost and performance", [
                "dbt catalog", "lineage", "column-level lineage", "explorer",
                "optimize cost", "model timing", "data health",
            ]),
            "8.2": ("Using dbt Catalog to find public models and cross-project references", [
                "find public model", "catalog search", "discover model",
                "cross-project reference",
            ]),
        },
    },
}


# --------------------------------------------------------------------------- #
# Question formats. Both guides list the same six.
# --------------------------------------------------------------------------- #

QUESTION_TYPES = {
    "multiple_choice": {
        "answer_shape": "single letter, e.g. 'B'",
        "partial_credit": False,
    },
    "multiple_response": {
        "answer_shape": "sorted letters, e.g. 'A,C' — exact-set match required",
        "partial_credit": False,
    },
    "fill_in_blank": {
        "answer_shape": "string; graded against `accepted_answers` after normalization",
        "partial_credit": False,
    },
    "matching": {
        "answer_shape": "dict {left_item: right_item}",
        "partial_credit": True,
    },
    "hotspot": {
        "answer_shape": "list of target ids selected from `hotspot_targets`",
        "partial_credit": True,
    },
    "build_list": {
        "answer_shape": "ordered list of item ids — order is graded",
        "partial_credit": True,
    },
    "domc": {
        "answer_shape": "dict {option_letter: 'Y'|'N'} — Discrete Option Multiple Choice",
        "partial_credit": False,
    },
}

NON_LETTER_TYPES = {"fill_in_blank", "matching", "hotspot", "build_list"}

# The official AE sample questions use four OR five options for single-answer items,
# so the gate must not insist on exactly four.
OFFICIAL_OPTION_COUNTS = (4, 5)

DIFFICULTY_LADDER = ["L1", "L2", "L3", "L4", "L5"]

VALID_STATUS = {"unsealed", "verified", "concept-only", "disputed"}

SEAL_CONFIDENCE_FLOOR = 70

AUTHORITATIVE_HOSTS = ("docs.getdbt.com", "getdbt.com", "learn.getdbt.com")

ID_PREFIXES = {
    "authored": "Q-AU-{code}",
    "official": "Q-OF-{code}",
    "community": "Q-CO-{code}",
    "practice": "Q-PA-{code}",
}


# --------------------------------------------------------------------------- #
# Derived lookups. Import these rather than recomputing.
# --------------------------------------------------------------------------- #

VALID_TRACKS = tuple(EXAM_FACTS)
VALID_DOMAINS = frozenset(DOMAINS)


def domains_for(track: str) -> dict[str, dict]:
    return {d: v for d, v in DOMAINS.items() if v["track"] == track}


def track_of(domain: str) -> Optional[str]:
    d = DOMAINS.get(domain)
    return d["track"] if d else None


def domain_dir(domain: str) -> Optional[str]:
    """knowledge/ fragment for a domain, e.g. 'ae/01-developing-and-optimizing-models'."""
    d = DOMAINS.get(domain)
    return f"{d['track']}/{d['dir']}" if d else None


def domain_by_dir(track: str, dirname: str) -> Optional[str]:
    for did, d in DOMAINS.items():
        if d["track"] == track and d["dir"] == dirname:
            return did
    return None


def task_title(domain: str, task_id: str) -> Optional[str]:
    d = DOMAINS.get(domain)
    if not d:
        return None
    entry = d["tasks"].get(task_id)
    return entry[0] if entry else None


def subtopic_share(track: str) -> dict[str, float]:
    """Share of the track's sub-topics held by each domain, as a percentage.

    NOT an official weight. dbt Labs publishes no per-topic weighting. This is the most
    defensible available proxy: the study guide enumerates sub-topics, and a topic with
    14 of them plainly covers more ground than one with 2. Use it to allocate study
    time, never to claim what the exam contains.
    """
    scope = domains_for(track)
    total = sum(len(d["tasks"]) for d in scope.values()) or 1
    return {did: round(100 * len(d["tasks"]) / total, 1) for did, d in scope.items()}


def estimated_questions(track: str) -> dict[str, float]:
    """Sub-topic share applied to the published 65-question length. A proxy, not a fact."""
    count = EXAM_FACTS[track]["question_count"]
    return {did: round(count * pct / 100, 1) for did, pct in subtopic_share(track).items()}


def id_prefix(provenance: str, track: str) -> str:
    return ID_PREFIXES[provenance].format(code=EXAM_FACTS[track]["code"])


def classify_domain(text: str, track: Optional[str] = None) -> tuple[Optional[str], int]:
    """Heuristic domain classifier: (domain_id, hit_count). Indicative, not certified."""
    low = (text or "").lower()
    scope = domains_for(track) if track else DOMAINS
    best, best_hits = None, 0
    for did, d in scope.items():
        hits = sum(1 for _, kws in d["tasks"].values() for k in kws if k.lower() in low)
        if hits > best_hits:
            best, best_hits = did, hits
    return best, best_hits


def classify_task(text: str, domain: str) -> tuple[Optional[str], int]:
    """Pick the best-matching task inside an already-known domain."""
    d = DOMAINS.get(domain)
    if not d:
        return None, 0
    low = (text or "").lower()
    best, best_hits = None, 0
    for task_id, (_, kws) in d["tasks"].items():
        hits = sum(1 for k in kws if k.lower() in low)
        if hits > best_hits:
            best, best_hits = task_id, hits
    return best, best_hits
