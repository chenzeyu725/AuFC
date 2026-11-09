# AuFC

# Generic private-site scheduler

Copy only this directory's `run.py` and `.github/workflows/refresh.yml` to the public runner repository. Keep the site's source, trainer, datasets, model artifacts, and credentials private.

Repository secrets: `SITE_URL`, `SITE_ACCESS_TOKEN` (private Sites service token), and `JOB_TOKEN` (site updater token). The workflow only accepts scheduled or owner-triggered runs; it has no pull-request trigger or write permission and publishes no artifacts or data caches.

Collection is requested every five minutes at minutes 2, 7, …, 57. GitHub can delay or drop runs; this is best-effort scheduling. Weekly training starts Sunday 02:17 Asia/Taipei (Saturday 18:17 UTC). The owner can manually run `train` once after setup for initial bootstrap. Each cloud runner downloads the private trainer to an ephemeral directory, installs its dependencies without caching, runs it, and removes the directory when finished.

Public repository schedules may automatically stop after sixty days without repository activity. The website must show last successful collection and stale status; the owner may need to re-enable the workflow. There is no laptop dependency and no guarantee of uninterrupted scheduling.
