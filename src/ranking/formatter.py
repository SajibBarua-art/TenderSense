"""Output formatter for rendering TenderSense daily shortlists in multiple formats."""
from typing import Dict, Any, List
from tabulate import tabulate

from src.models.pipeline import DailyShortlist, ProcessedTender


class ShortlistFormatter:
    """Formats ranked tender results into text tables, Markdown, and JSON."""

    @staticmethod
    def format_as_table(shortlist: DailyShortlist) -> str:
        """Formats the shortlist as an aligned ASCII/Unicode table for terminal display."""
        headers = ["Grade", "Action", "ID", "Portal", "Deadline", "Urgency", "Score", "Title"]
        rows = []

        for item in shortlist.tenders:
            deadline_str = f"{item.days_until_deadline}d ({item.closing_date or 'N/A'})"
            title_truncated = (item.title[:45] + "...") if len(item.title) > 45 else item.title
            rows.append([
                f"[{item.match_grade.value}]",
                item.recommendation.value,
                item.tender_id,
                item.source_portal,
                deadline_str,
                item.urgency_flag.value,
                f"{item.semantic_result.similarity_score:.2f}",
                title_truncated,
            ])

        table_str = tabulate(rows, headers=headers, tablefmt="fancy_grid")
        summary_header = (
            f"\n=======================================================\n"
            f"   TENDERSENSE DAILY SHORTLIST ({shortlist.generated_at.strftime('%Y-%m-%d %H:%M UTC')})\n"
            f"   Total: {shortlist.total_evaluated} | "
            f"Eligible: {shortlist.eligible_count} | "
            f"Ineligible: {shortlist.ineligible_count}\n"
            f"   Recommendations -> BID: {shortlist.bid_count} | "
            f"HOLD: {shortlist.hold_count} | "
            f"SKIP: {shortlist.skip_count}\n"
            f"   Grades -> S: {shortlist.grade_s_count} | "
            f"A: {shortlist.grade_a_count} | "
            f"B: {shortlist.grade_b_count} | "
            f"C: {shortlist.grade_c_count}\n"
            f"=======================================================\n"
        )
        return summary_header + table_str

    @staticmethod
    def format_as_markdown(shortlist: DailyShortlist) -> str:
        """Formats the shortlist as rich GitHub-flavored Markdown."""
        lines = [
            f"# TenderSense Daily Shortlist",
            f"*Generated on: {shortlist.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "## Executive Summary",
            f"- **Total Tenders Processed**: {shortlist.total_evaluated}",
            f"- **Eligible Bids**: {shortlist.eligible_count} | **Flagged Ineligible**: {shortlist.ineligible_count}",
            f"- **Action Breakdown**: **{shortlist.bid_count} BID** | **{shortlist.hold_count} HOLD** | **{shortlist.skip_count} SKIP**",
            f"- **Match Grades**: **{shortlist.grade_s_count} S-Tier** | **{shortlist.grade_a_count} A-Tier** | **{shortlist.grade_b_count} B-Tier** | **{shortlist.grade_c_count} C-Tier**",
            "",
            "## Ranked Shortlist",
            "| Grade | Recommendation | Tender ID | Portal | Days Left | Urgency | Score | Title | AI Strategic Summary |",
            "|:---:|:---:|:---|:---|:---:|:---:|:---:|:---|:---|",
        ]

        for item in shortlist.tenders:
            title_escaped = item.title.replace("|", "/")
            summary_escaped = item.ai_summary.replace("|", "/")
            lines.append(
                f"| **{item.match_grade.value}** | **{item.recommendation.value}** | `{item.tender_id}` | "
                f"{item.source_portal} | {item.days_until_deadline}d | `{item.urgency_flag.value}` | "
                f"{item.semantic_result.similarity_score:.2f} | {title_escaped} | {summary_escaped} |"
            )

        return "\n".join(lines)


shortlist_formatter = ShortlistFormatter()
