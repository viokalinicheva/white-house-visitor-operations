# White House Visitor Operations and Demand Planning

How can operations analysts learn from historical public appointment records without mistaking them for attendance or exposing visitors? This project harmonizes 25 official releases into an aggregate-only visual story about activity concentration and coverage.

## Verified findings

- **1,207,458 source rows** from the 2021 annual file and 24 monthly 2022–2023 files.
- **1,202 exact duplicate rows removed within their source release**, leaving **1,206,256 records**. No repeated full-row hashes were found across releases after header harmonization.
- All scheduled start dates parsed successfully and fall within January 20, 2021–December 31, 2023; all 36 calendar months have records. Policy coverage in 2021 is partial.
- Annual disclosed-record totals after deduplication: **41,405 (2021), 322,689 (2022), and 842,162 (2023)**.
- The location code **WH represents 980,186 records (81.3%)**; it remains visible instead of being removed to highlight smaller sites.
- Among 1,053 dates with records, the median is **330 records/day**, the 95th percentile approximately **4,022**, and the largest daily count **11,205**. Dates and individual schedules are not exported.

The unit is a **disclosed appointment-access record**, not a unique person, realized visit, meeting, or staff workload hour. These data cannot establish actual attendance, staffing requirements, political access, influence, or causal changes in demand.

## Inspect the work

- [Executed visual-story notebook](white_house_visitor_operations.ipynb): aggregate raw-data audit, four figures, interpretations, ethics, limits, and call to action.
- [Analysis implementation](analysis.py): one-file-at-a-time ingestion, schema harmonization, within-file deduplication, date validation, count reconciliation, and privacy-preserving exports.
- [Validation record](validation.json): six fresh-kernel code cells executed; zero saved errors; source and code hashes and actual metrics.
- Four figures and aggregate summaries are embedded in the executed notebook. A rerun also generates local `outputs/` files; that folder is not part of the root-only public release. There are no person-level logs, names, identifiers, room records, row samples, or daily schedules in the published package.

## Source and responsible use

The [official archived visitor-log index](https://bidenwhitehouse.archives.gov/disclosures/visitor-logs/) links the 25 source files. [sources.json](sources.json) records individual release URLs and exact SHA-256 hashes. The [voluntary disclosure policy](https://bidenwhitehouse.archives.gov/voluntary-disclosure/) excludes some staff, personal, sensitive-meeting, and security-related records. These logs are therefore not all White House activity. The [copyright policy](https://bidenwhitehouse.archives.gov/copyright/) states that government-produced material is not copyright protected; third-party material can have different terms. Sources checked **October 28, 2026**.

Public availability does not eliminate privacy responsibilities. This package does not redistribute raw logs or match named people. Raw inputs remain outside the repository. Outputs contain only monthly counts, broad location totals, a calendar summary, and a histogram of daily count distribution. No individual record examples are shown. Code and original writing are MIT; see [LICENSE](LICENSE).

## Reproduce from the official raw releases

Use Python 3.12 (verified on 3.12.14). Raw files together are approximately 216 MB; the workflow processes one release at a time and retains only a narrow internal analytical frame. Keep at least 1 GB of available memory and sufficient disk space for the downloads and environment.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analysis.py --download-data /absolute/path/outside-this-repo/visitor-data
export PROJECT_DATA_DIR=/absolute/path/outside-this-repo/visitor-data
MPLBACKEND=Agg python analysis.py --run
```

The downloader requests only the 25 official release URLs, validates their frozen hashes, refuses to overwrite mismatching sources, and rejects destinations inside the repository. No credentials are needed. Source files are not modified. Network access is needed for acquisition, not the subsequent analysis.

For the notebook, select that environment and **Restart Kernel and Run All** from the repository directory. Alternatively install its kernel with `python -m ipykernel install --sys-prefix --name python3` and run `jupyter execute white_house_visitor_operations.ipynb --inplace --kernel_name=python3`. All 25 files were read from original raw inputs in the validated fresh-kernel run; no aggregate-cache shortcut was used. The downloader was independently tested against all 25 official release URLs, and every downloaded file matched the frozen hash.

## Analytical decisions and limits

Legacy headers are harmonized before aggregation, with original values read as strings for consistent exact-row checks. Exact duplicates are removed **within a release**; raw and cleaned counts remain in validation.json so this small choice is transparent. Cross-release row hashes are an internal duplicate sensitivity audit, not person matching. Missing start dates, invalid dates, and dates outside the study scope are counted explicitly. Monthly aggregates reconcile to the analysis row count.

The cancellation field is populated for 815 retained records and parses as a date for 812; the three unparseable entries remain flagged. Blank cancellation fields do **not** establish attendance. `Total People` is not summed because group totals can repeat across person-level records. The dominant location is retained; no location-code meaning is invented. Absent observed days are not treated as zero actual activity. Three heterogeneous years, including pandemic-era and partial policy coverage, do not support an unqualified seasonal forecast.

The defensible next step is to obtain aggregate realized arrivals, cancellation definitions, event calendars, service times, and staffing measures before forecasting resources. This release repairs the original notebook's overstatement of records as visits and of three years as stable seasonality. It also removes identity-bearing preview output and unnecessary daily schedule exposure. Original course materials remain preserved. The four figures were visually checked for labels, scales, legibility, coverage notes, and absence of person-level details.
