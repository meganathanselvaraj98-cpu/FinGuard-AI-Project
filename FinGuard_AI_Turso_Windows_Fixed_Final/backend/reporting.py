"""CSV, Excel dashboard, and PDF report generation."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.analytics import calculate_kpis, category_summary, monthly_summary

SAFE_DROP_COLUMNS = ["transaction_id", "fingerprint", "account_number", "ifsc", "pan", "phone", "address"]


def safe_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    safe = df.drop(columns=SAFE_DROP_COLUMNS, errors="ignore").copy()
    if "date" in safe:
        safe["date"] = pd.to_datetime(safe["date"], errors="coerce")
    return safe


def csv_bytes(df: pd.DataFrame) -> bytes:
    return safe_export_dataframe(df).to_csv(index=False).encode("utf-8-sig")


def excel_dashboard_bytes(df: pd.DataFrame, title: str = "FinGuard AI Financial Report") -> bytes:
    output = io.BytesIO()
    safe_df = safe_export_dataframe(df)
    kpis = calculate_kpis(safe_df)
    monthly = monthly_summary(safe_df)
    categories = category_summary(safe_df)
    payments = (
        safe_df[safe_df["type"] == "EXPENSE"].groupby("payment_mode", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        if not safe_df.empty
        else pd.DataFrame(columns=["payment_mode", "amount"])
    )
    merchants = (
        safe_df[safe_df["type"] == "EXPENSE"].groupby("merchant", as_index=False)["amount"].sum().nlargest(20, "amount")
        if not safe_df.empty
        else pd.DataFrame(columns=["merchant", "amount"])
    )
    statements = (
        safe_df.groupby(["statement_label", "account_last4"], dropna=False, as_index=False)
        .agg(transactions=("id", "size"), income=("amount", lambda values: float(values[safe_df.loc[values.index, "type"].eq("INCOME")].sum())), expense=("amount", lambda values: float(values[safe_df.loc[values.index, "type"].eq("EXPENSE")].sum())))
        if not safe_df.empty and {"statement_label", "account_last4"}.issubset(safe_df.columns)
        else pd.DataFrame(columns=["statement_label", "account_last4", "transactions", "income", "expense"])
    )

    with pd.ExcelWriter(output, engine="xlsxwriter", datetime_format="dd-mmm-yyyy hh:mm") as writer:
        workbook = writer.book
        dashboard = workbook.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = dashboard

        title_fmt = workbook.add_format({"bg_color": "#07111F", "font_color": "#FFFFFF", "bold": True, "font_size": 20, "align": "center", "valign": "vcenter"})
        subtitle_fmt = workbook.add_format({"bg_color": "#0B1726", "font_color": "#91A7C2", "italic": True, "align": "center"})
        card_fmt = workbook.add_format({"bg_color": "#122238", "font_color": "#FFFFFF", "bold": True, "font_size": 14, "align": "center", "valign": "vcenter", "border": 1, "border_color": "#2B4A69", "text_wrap": True})
        note_fmt = workbook.add_format({"font_color": "#6B7E92", "italic": True, "text_wrap": True})
        currency_fmt = workbook.add_format({"num_format": '₹#,##0.00;[Red]-₹#,##0.00'})
        percent_fmt = workbook.add_format({"num_format": "0.0%"})

        dashboard.hide_gridlines(2)
        dashboard.set_column("A:J", 16)
        dashboard.set_row(0, 36)
        dashboard.merge_range("A1:J1", title, title_fmt)
        dashboard.merge_range("A2:J2", f"Generated {datetime.now():%d %B %Y, %I:%M %p} · Privacy-safe export", subtitle_fmt)

        cards = [
            ("A4:B6", "Total Income", f"₹{kpis['income']:,.2f}"),
            ("C4:D6", "Total Expense", f"₹{kpis['expense']:,.2f}"),
            ("E4:F6", "Net Savings", f"₹{kpis['savings']:,.2f}"),
            ("G4:H6", "Savings Rate", f"{kpis['savings_rate']:.1f}%"),
            ("I4:J6", "Transactions", f"{int(kpis['transactions']):,}"),
        ]
        for cell_range, label, value in cards:
            dashboard.merge_range(cell_range, f"{label}\n{value}", card_fmt)

        sheets = {
            "Transactions": safe_df,
            "Monthly Summary": monthly,
            "Category Summary": categories,
            "Payment Modes": payments,
            "Top Merchants": merchants,
            "Statement Summary": statements,
        }
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            worksheet.set_column(0, max(len(frame.columns) - 1, 0), 18)
            if len(frame) > 0 and len(frame.columns) > 0:
                worksheet.add_table(0, 0, len(frame), len(frame.columns) - 1, {"name": f"Tbl{sheet_name.replace(' ', '')}", "columns": [{"header": str(column)} for column in frame.columns], "style": "Table Style Medium 2"})
            elif len(frame.columns) > 0:
                worksheet.autofilter(0, 0, 0, len(frame.columns) - 1)
            for index, column in enumerate(frame.columns):
                if column in {"amount", "income", "expense", "savings", "cash_flow", "total", "average"}:
                    worksheet.set_column(index, index, 18, currency_fmt)
                elif column in {"savings_rate", "share_percent"}:
                    worksheet.set_column(index, index, 16, workbook.add_format({"num_format": "0.0"}))

        if not monthly.empty:
            line = workbook.add_chart({"type": "line"})
            for column_index, name in [(1, "Income"), (2, "Expense"), (4, "Savings")]:
                line.add_series({"name": name, "categories": ["Monthly Summary", 1, 0, len(monthly), 0], "values": ["Monthly Summary", 1, column_index, len(monthly), column_index], "line": {"width": 2.25}})
            line.set_title({"name": "Monthly Income, Expense and Savings"})
            line.set_x_axis({"name": "Month"})
            line.set_y_axis({"name": "INR", "num_format": "₹#,##0"})
            line.set_style(10)
            dashboard.insert_chart("A8", line, {"x_scale": 1.45, "y_scale": 1.25})

        if not categories.empty:
            doughnut = workbook.add_chart({"type": "doughnut"})
            display_count = min(10, len(categories))
            doughnut.add_series({"name": "Category Spending", "categories": ["Category Summary", 1, 0, display_count, 0], "values": ["Category Summary", 1, 1, display_count, 1], "data_labels": {"percentage": True}})
            doughnut.set_title({"name": "Top Expense Categories"})
            doughnut.set_hole_size(55)
            doughnut.set_style(10)
            dashboard.insert_chart("F8", doughnut, {"x_scale": 1.25, "y_scale": 1.25})

        if not payments.empty:
            bar = workbook.add_chart({"type": "bar"})
            bar.add_series({"name": "Expense", "categories": ["Payment Modes", 1, 0, len(payments), 0], "values": ["Payment Modes", 1, 1, len(payments), 1]})
            bar.set_title({"name": "Payment Mode Analysis"})
            bar.set_style(11)
            dashboard.insert_chart("A25", bar, {"x_scale": 1.45, "y_scale": 1.15})

        dashboard.merge_range("F25:J27", "Excel tables include filter dropdowns for interactive exploration. Native Excel slicers are not generated because they are not supported reliably by the portable Python writer; pivot-style summary sheets and charts are included instead.", note_fmt)

    return output.getvalue()


def _table_style(header_color: str = "#10243C") -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7C4")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )


def pdf_report_bytes(df: pd.DataFrame, user_name: str) -> bytes:
    safe_df = safe_export_dataframe(df)
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("FinGuard AI — Personal Finance Report", styles["Title"]),
        Paragraph(f"Prepared for: {user_name}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now():%d %B %Y, %I:%M %p}", styles["Normal"]),
        Spacer(1, 8),
    ]
    kpis = calculate_kpis(safe_df)
    summary_data = [
        ["Metric", "Value"],
        ["Total Income", f"INR {kpis['income']:,.2f}"],
        ["Total Expense", f"INR {kpis['expense']:,.2f}"],
        ["Net Savings", f"INR {kpis['savings']:,.2f}"],
        ["Savings Rate", f"{kpis['savings_rate']:.1f}%"],
        ["Transaction Count", f"{int(kpis['transactions'])}"],
    ]
    summary_table = Table(summary_data, colWidths=[70 * mm, 80 * mm])
    summary_table.setStyle(_table_style())
    story.extend([summary_table, Spacer(1, 12)])

    categories = category_summary(safe_df).head(10)
    if not categories.empty:
        story.append(Paragraph("Top Expense Categories", styles["Heading2"]))
        rows = [["Category", "Total", "Share"]]
        for _, row in categories.iterrows():
            rows.append([str(row["category"]), f"INR {float(row['total']):,.2f}", f"{float(row['share_percent']):.1f}%"])
        table = Table(rows, colWidths=[80 * mm, 45 * mm, 30 * mm], repeatRows=1)
        table.setStyle(_table_style("#1E6B5C"))
        story.extend([table, Spacer(1, 12)])

    if not safe_df.empty:
        story.append(PageBreak())
        story.append(Paragraph("Recent Transactions", styles["Heading2"]))
        rows = [["Date", "Description", "Type", "Category", "Amount"]]
        for _, row in safe_df.sort_values("date", ascending=False).head(25).iterrows():
            rows.append([
                pd.Timestamp(row["date"]).strftime("%d-%m-%Y"),
                str(row["description"])[:30],
                str(row["type"]),
                str(row.get("category", ""))[:18],
                f"INR {float(row['amount']):,.2f}",
            ])
        tx_table = Table(rows, colWidths=[24 * mm, 63 * mm, 22 * mm, 31 * mm, 32 * mm], repeatRows=1)
        tx_table.setStyle(_table_style("#1E6B5C"))
        story.append(tx_table)

    story.extend([
        Spacer(1, 10),
        Paragraph("Privacy note: Full account numbers, IFSC codes, PAN, phone, address, and decrypted transaction references are excluded. Investment content is educational and is not regulated financial advice.", styles["Italic"]),
    ])
    document.build(story)
    return output.getvalue()
