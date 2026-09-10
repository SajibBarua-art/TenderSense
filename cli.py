"""Command-line interface (CLI) for executing TenderSense pipeline workflows."""
import argparse
import sys
import time

from src.orchestration.engine import orchestrator
from src.ranking.formatter import shortlist_formatter


def main():
    parser = argparse.ArgumentParser(
        description="TenderSense CLI: Automated Procurement Monitoring & Shortlisting Engine for BracIT"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run ingestion, rules evaluation, matching, and shortlisting")
    run_parser.add_argument(
        "--source",
        type=str,
        default="test_dataset",
        choices=["test_dataset", "egp_bd", "world_bank", "all"],
        help="Procurement source to ingest (default: test_dataset)"
    )
    run_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tenders to process (default: all available)"
    )
    run_parser.add_argument(
        "--format",
        type=str,
        default="table",
        choices=["table", "markdown", "json"],
        help="Output format (default: table)"
    )

    # Command: profile
    subparsers.add_parser("profile", help="Display BracIT capability profile summary")

    args = parser.parse_args()

    if args.command == "profile":
        profile = orchestrator.get_profile()
        print(f"\n================ BRACIT CAPABILITY PROFILE ================")
        print(f"Company: {profile.company_name}")
        print(f"Tagline: {profile.tagline}")
        print(f"Turnover: {profile.annual_turnover_bdt:,.0f} BDT (~${profile.annual_turnover_usd:,.0f} USD)")
        print(f"Personnel: {profile.total_staff} staff | Operating: {', '.join(profile.operating_regions)}")
        print(f"\nCore Services ({len(profile.services)}):")
        for s in profile.services:
            print(f"  - [{s.service_id}] {s.name}")
        print(f"\nPast Projects ({len(profile.past_projects)}):")
        for p in profile.past_projects:
            print(f"  - [{p.project_id}] {p.name} (Client: {p.client}, Value: {p.value_bdt:,.0f} BDT)")
        print(f"\nCertifications ({len(profile.certifications)}):")
        for c in profile.certifications:
            print(f"  - {c.name} (Code: {c.standard_code}, Valid: {c.valid_until})")
        print("===========================================================\n")
        return

    # Default to run command if none specified
    source = getattr(args, "source", "test_dataset")
    limit = getattr(args, "limit", None)
    output_format = getattr(args, "format", "table")

    print(f"\n[TenderSense] Starting pipeline for source='{source}' (limit={limit or 'all'})...")
    start = time.perf_counter()
    shortlist = orchestrator.run_pipeline(source=source, limit=limit)
    duration = time.perf_counter() - start

    if output_format == "table":
        print(shortlist_formatter.format_as_table(shortlist))
    elif output_format == "markdown":
        print(shortlist_formatter.format_as_markdown(shortlist))
    elif output_format == "json":
        print(shortlist.model_dump_json(indent=2))

    print(f"[TenderSense] Completed in {duration:.3f}s. Average {duration / max(1, shortlist.total_evaluated) * 1000:.1f}ms per tender.\n")


if __name__ == "__main__":
    main()
