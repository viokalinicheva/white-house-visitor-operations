"""Privacy-preserving analysis of disclosed appointment-record activity."""
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile
import numpy as np
import pandas as pd
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="portfolio-mpl-"))
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import StrMethodFormatter

ROOT = Path(__file__).resolve().parent
BLUE, GRAY = "#176B87", "#697586"
RENAME = {"NAMELAST": "Last Name", "NAMEFIRST": "First Name", "NAMEMID": "Middle Initial",
          "ACCESS_TYPE": "Access Type", "APPT_MADE_DATE": "Appointment Made Date",
          "APPT_START_DATE": "Appointment Start Date", "APPT_END_DATE": "Appointment End Date",
          "APPT_CANCEL_DATE": "Appointment Cancel Date", "TOTAL_PEOPLE": "Total People",
          "LAST_UPDATEDBY": "Last Updated By", "LASTENTRYDATE": "Last Entry Date",
          "TERMINAL_SUFFIX": "Terminal Suffix", "VISITEE_NAMELAST": "Visitee Last Name",
          "VISITEE_NAMEFIRST": "Visitee First Name", "MEETING_LOC": "Meeting Location",
          "MEETING_ROOM": "Meeting Room", "CALLER_NAME_LAST": "Caller Last Name",
          "CALLER_NAME_FIRST": "Caller First Name", "CALLER_ROOM": "Caller Room",
          "RELEASEDATE": "Release Date"}


def source_hash(path):
    with path.open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()


def setup():
    plt.rcParams.update({"figure.dpi": 120, "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlepad": 16})
    (ROOT / "outputs").mkdir(exist_ok=True)


def load_and_audit():
    # I am reading one source file at a time; identities never enter notebook outputs or exports.
    folder = Path(os.environ.get("PROJECT_DATA_DIR", "data"))
    manifest = json.loads((ROOT / "sources.json").read_text())
    pieces, inventory, missing, hashes = [], [], {}, []
    raw_count = duplicates = 0
    for spec in manifest["files"]:
        path = folder / spec["file"]
        digest = source_hash(path)
        if digest != spec["sha256"]: raise ValueError(f"Snapshot mismatch: {path.name}")
        raw = pd.read_csv(path, dtype="string", low_memory=False)
        # I am normalizing headers only and retaining original values for exact duplicate checks.
        raw = raw.rename(columns=RENAME)
        assert raw.columns.is_unique
        duplicate_mask = raw.duplicated()
        n_duplicates = int(duplicate_mask.sum())
        raw_count += len(raw); duplicates += n_duplicates
        clean = raw.loc[~duplicate_mask].copy()
        # Hashes permit an unpublished cross-release duplicate sensitivity check without exporting identities.
        comparable = clean.drop(columns=[x for x in clean if x.startswith("Unnamed:")], errors="ignore")
        hashes.append(pd.util.hash_pandas_object(comparable.reindex(sorted(comparable.columns), axis=1).fillna(""), index=False))
        dates = pd.to_datetime(clean["Appointment Start Date"], format="mixed", errors="coerce")
        cancel_dates = pd.to_datetime(clean["Appointment Cancel Date"], format="mixed", errors="coerce")
        for column in ["Appointment Start Date", "Meeting Location", "Appointment Cancel Date"]:
            missing[column] = missing.get(column, 0) + int(clean[column].isna().sum())
        inventory.append({"file": path.name, "rows": len(raw), "columns": len(raw.columns),
                          "exact_duplicates_removed_within_file": n_duplicates,
                          "invalid_start_dates": int(dates.isna().sum()), "sha256": digest})
        pieces.append(pd.DataFrame({"date": dates.dt.normalize(),
                                    "location": clean["Meeting Location"].str.strip().fillna("Not recorded"),
                                    "cancel_recorded": clean["Appointment Cancel Date"].notna(),
                                    "cancel_parsed": cancel_dates.notna()}))
        del raw, clean, comparable
    frame = pd.concat(pieces, ignore_index=True)
    assert len(frame) == raw_count - duplicates
    valid = frame.loc[frame["date"].notna()].copy()
    # I am restricting the story to scheduled dates in the stated 2021–2023 window.
    in_scope = valid["date"].between("2021-01-20", "2023-12-31")
    scope = valid.loc[in_scope].copy()
    scope["month"] = scope["date"].dt.to_period("M")
    monthly = scope.groupby("month").size()
    assert monthly.sum() == len(scope)
    row_hashes = pd.concat(hashes, ignore_index=True)
    cross_release_repeated_hashes = int(row_hashes.duplicated().sum())
    facts = {"raw_rows": raw_count, "source_files": len(inventory),
             "exact_duplicates_removed_within_file": duplicates,
             "rows_after_within_file_deduplication": len(frame),
             "cross_release_repeated_row_hashes": cross_release_repeated_hashes,
             "invalid_start_dates": int(frame["date"].isna().sum()),
             "valid_dates_outside_scope": int((~in_scope).sum()),
             "analysis_records": len(scope), "first_date": str(scope["date"].min().date()),
             "last_date": str(scope["date"].max().date()), "months_present": len(monthly),
             "missing_by_selected_field": missing,
             "cancel_field_nonmissing": int(frame["cancel_recorded"].sum()),
             "cancel_field_parsed": int(frame["cancel_parsed"].sum()), "inventory": inventory}
    return scope, facts


def save(fig, name):
    fig.savefig(ROOT / "outputs" / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.show()


def monthly_story(frame, facts):
    monthly = frame.groupby("month").size()
    full = pd.period_range("2021-01", "2023-12", freq="M")
    counts = monthly.reindex(full)
    annual = frame.groupby(frame["date"].dt.year).size()
    facts["annual_records"] = {str(k): int(v) for k, v in annual.items()}
    facts["monthly_peak"] = {"month": str(monthly.idxmax()), "records": int(monthly.max())}
    facts["monthly_low"] = {"month": str(monthly.idxmin()), "records": int(monthly.min())}
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(counts.index.to_timestamp(), counts, color=BLUE, marker="o", markersize=3)
    ax.set(title="Published appointment-record activity is much higher in 2023",
           ylabel="Disclosed appointment records (not attendance)", xlabel="Scheduled appointment month")
    ax.set_ylim(bottom=0); ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.annotate(f"{monthly.max():,}", (monthly.idxmax().to_timestamp(), monthly.max()), xytext=(-7, 9), textcoords="offset points", ha="right")
    fig.text(.01, -.02, "25 frozen public releases. 2021 is partial; missing months are not silently treated as zero. Exempt records are not disclosed.", fontsize=9)
    save(fig, "01_monthly_activity")
    monthly.rename("appointment_records").to_csv(ROOT / "outputs" / "monthly_activity.csv")
    return pd.DataFrame({"year": annual.index, "appointment_records": annual.values})


def location_story(frame, facts):
    counts = frame["location"].value_counts()
    facts["leading_location"] = {"code": str(counts.index[0]), "records": int(counts.iloc[0]),
                                 "pct": 100 * float(counts.iloc[0]) / len(frame)}
    # I am keeping the dominant location instead of hiding it; small cells are grouped for privacy.
    top = counts.head(5).copy()
    plot = pd.concat([top, pd.Series({"Other / not recorded": counts.iloc[5:].sum()})])
    if (plot < 10).any(): plot = plot.loc[plot >= 10]
    fig, ax = plt.subplots(figsize=(10, 4.6)); plot = plot.sort_values()
    bars = ax.barh(plot.index, plot, color=BLUE)
    for b, n in zip(bars, plot): ax.text(n+counts.max()*.01, b.get_y()+b.get_height()/2, f"{n:,} ({n/len(frame):.1%})", va="center")
    ax.set_xlim(0, counts.max()*1.3); ax.set(title="The dominant meeting-location code must remain visible",
                                          xlabel="Disclosed appointment records", ylabel="Meeting-location code")
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    fig.text(.01, -.02, "Location codes are retained as recorded. No room-level details, identities, or individual appointments are published.", fontsize=9)
    save(fig, "02_location_concentration")
    plot.rename("appointment_records").to_csv(ROOT / "outputs" / "location_summary.csv")
    return plot.rename("records").to_frame()


def workload_story(frame, facts):
    daily = frame.groupby("date").size()
    observed = daily.copy()
    facts["days_with_records"] = len(daily)
    facts["daily_median_among_observed_days"] = float(daily.median())
    facts["daily_p95_among_observed_days"] = float(daily.quantile(.95))
    facts["largest_day_records"] = int(daily.max())
    facts["peak_day_to_median_ratio"] = float(daily.max() / daily.median())
    # I am displaying a distribution of workload days, not a potentially identifying appointment schedule.
    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.hist(observed, bins=35, color=BLUE, edgecolor="white")
    ax.axvline(observed.median(), color="#C55A11", lw=2, label=f"Median: {observed.median():,.0f}")
    ax.axvline(observed.quantile(.95), color=GRAY, ls="--", lw=2, label=f"95th percentile: {observed.quantile(.95):,.0f}")
    ax.set(title="A typical recorded day understates the upper-tail workload",
           xlabel="Disclosed appointment records per observed scheduled day", ylabel="Days with at least one record")
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}")); ax.legend(frameon=False)
    fig.text(.01, -.02, "Only dates with disclosed records are included; unobserved dates cannot be assumed to have zero actual activity.", fontsize=9)
    save(fig, "03_daily_workload_distribution")
    return observed.describe(percentiles=[.5, .9, .95, .99]).to_frame("records_per_observed_day")


def calendar_story(frame, facts):
    totals = frame.groupby([frame["date"].dt.year, frame["date"].dt.month]).size().unstack().reindex(index=[2021, 2022, 2023], columns=range(1,13))
    fig, ax = plt.subplots(figsize=(11, 3.5))
    im = ax.imshow(totals, aspect="auto", cmap="Blues", vmin=0)
    ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(3), ["2021*", "2022", "2023"])
    for i in range(3):
        for j in range(12):
            v = totals.iloc[i,j]
            ax.text(j, i, "—" if pd.isna(v) else f"{v/1000:.1f}k", ha="center", va="center", fontsize=9,
                    color="white" if pd.notna(v) and v > np.nanmax(totals.values)*.55 else "black")
    ax.set(title="Three years do not establish a stable seasonal forecasting pattern", xlabel="Scheduled appointment month")
    fig.colorbar(im, ax=ax, label="Disclosed records")
    fig.text(.01, -.06, "*Policy begins January 20, 2021. A dash means no records observed, not confirmed zero attendance. No forecast is fitted.", fontsize=9)
    save(fig, "04_calendar_coverage")
    totals.to_csv(ROOT / "outputs" / "calendar_activity.csv", index_label="year")
    return totals


def download_inputs(destination):
    """Acquire public releases without putting person-level logs in the repository."""
    import urllib.request
    folder = Path(destination).expanduser().resolve()
    if folder == ROOT or ROOT in folder.parents:
        raise ValueError("Keep person-level source logs outside this public repository.")
    folder.mkdir(parents=True, exist_ok=True)
    for spec in json.loads((ROOT / "sources.json").read_text())["files"]:
        target = folder / spec["file"]
        if target.exists():
            if source_hash(target) != spec["sha256"]: raise ValueError(f"Existing snapshot mismatch: {target.name}")
            continue
        request = urllib.request.Request(spec["url"], headers={"User-Agent":"portfolio-reproducibility"})
        with urllib.request.urlopen(request, timeout=180) as response: payload = response.read()
        assert hashlib.sha256(payload).hexdigest() == spec["sha256"], f"Upstream mismatch: {target.name}"
        target.write_bytes(payload)
        print(f"Verified {target.name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-data", metavar="EXTERNAL_FOLDER")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.download_data: download_inputs(args.download_data)
    if args.run:
        setup(); frame, facts = load_and_audit()
        for fn in [monthly_story, location_story, workload_story, calendar_story]: fn(frame, facts)
        (ROOT / "outputs" / "metrics.json").write_text(json.dumps(facts, indent=2)+"\n")
