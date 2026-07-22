"""Prediction, financial health, anomaly, advisor, and investment-idea pages."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from backend.analytics import (
    calculate_health_score,
    calculate_kpis,
    detect_subscription_candidates,
    generate_advice,
    monthly_summary,
)
from backend.database import session_scope
from backend.ml_service import (
    compare_category_classifiers,
    detect_anomalies,
    forecast_monthly_expense,
    load_model_registry,
    predict_monthly_savings,
    train_financial_risk_classifier,
)
from backend.services import (
    get_user_preferences,
    save_prediction,
    save_user_preferences,
)
from frontend.charting import show_chart
from frontend.pages.dashboard import load_user_dataframe
from frontend.theme import hero


def _dark(fig, height: int = 370):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,11,20,.35)",
    )
    return fig


def _confusion_matrix_chart(
    matrix: list[list[int]],
    labels: list[str],
    title: str,
):
    if not matrix:
        return None

    frame = pd.DataFrame(
        matrix,
        index=[f"Actual {label}" for label in labels],
        columns=[f"Predicted {label}" for label in labels],
    )
    return _dark(px.imshow(frame, text_auto=True, title=title), 390)


def _prepare_anomaly_plot_data(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Convert anomaly results into Plotly-safe chart values."""
    plot_data = anomalies.copy()

    if "anomaly_score" not in plot_data.columns:
        plot_data["anomaly_score"] = 0.0

    plot_data["anomaly_score"] = pd.to_numeric(
        plot_data["anomaly_score"],
        errors="coerce",
    ).fillna(0.0)

    if "ml_anomaly" not in plot_data.columns:
        plot_data["ml_anomaly"] = False

    plot_data["ml_anomaly"] = (
        plot_data["ml_anomaly"]
        .fillna(False)
        .astype(bool)
    )

    plot_data["anomaly_strength"] = plot_data["anomaly_score"].abs()
    maximum_score = (
        float(plot_data["anomaly_strength"].max())
        if not plot_data.empty
        else 0.0
    )

    if not math.isfinite(maximum_score) or maximum_score <= 0:
        plot_data["marker_size"] = 12.0
    else:
        plot_data["marker_size"] = (
            8.0
            + (plot_data["anomaly_strength"] / maximum_score) * 24.0
        ).clip(lower=8.0, upper=32.0)

    return plot_data


def render_predictions_page(user_id: int) -> None:
    hero(
        "Smart insights",
        "Predictions & future planning",
        (
            "Estimate upcoming expenses and savings, understand category "
            "patterns, review financial risk, and identify unusual activity."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        st.info("Upload transactions before generating predictions.")
        return

    view = st.radio(
        "Prediction workspace",
        [
            "Prediction readiness",
            "Expense & savings forecast",
            "Category insights",
            "Financial risk",
            "Unusual activity",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    if view == "Prediction readiness":
        registry = pd.DataFrame(load_model_registry())
        ready = (
            int((registry["Status"] == "Ready").sum())
            if not registry.empty and "Status" in registry.columns
            else 0
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Prediction tools", len(registry))
        c2.metric("Ready tools", ready)
        c3.metric("User transaction rows", len(df))

        if st.session_state.get("user_role") == "ADMIN":
            st.dataframe(registry, width="stretch", hide_index=True)
        else:
            st.success("Prediction services are ready for your account.")
            st.caption(
                "Your financial records are analysed only inside your "
                "authenticated workspace."
            )
        return

    if view == "Expense & savings forecast":
        if st.session_state.get("user_role") == "ADMIN":
            with st.expander("Advanced evaluation details"):
                st.write(
                    "Regression comparison includes linear, tree-based, "
                    "neighbour-based, ensemble, and margin-based methods."
                )

        if st.button(
            "Generate expense and savings forecast",
            type="primary",
            width="stretch",
        ):
            with st.spinner("Preparing your forecast..."):
                st.session_state[f"forecast_{user_id}"] = (
                    forecast_monthly_expense(df, user_id)
                )
                st.session_state[f"savings_{user_id}"] = (
                    predict_monthly_savings(df, user_id)
                )

        result = st.session_state.get(f"forecast_{user_id}")
        savings_result = st.session_state.get(f"savings_{user_id}")

        if not result or not savings_result:
            st.info(
                "Generate the forecast to see next-month expense and "
                "savings estimates."
            )
            return

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Predicted next-month expense",
            f"₹{float(result['prediction']):,.0f}",
        )
        c2.metric(
            "Estimated next-month savings",
            f"₹{float(savings_result['prediction']):,.0f}",
        )
        c3.metric("Forecast status", "Ready")

        if st.session_state.get("user_role") == "ADMIN":
            model_text = f"Savings model: {savings_result.get('model', 'N/A')}"
            if savings_result.get("mae") is not None:
                model_text += f" · MAE ₹{float(savings_result['mae']):,.0f}"
            st.caption(model_text)

        if result.get("metrics") and st.session_state.get("user_role") == "ADMIN":
            metrics_df = pd.DataFrame(result["metrics"])
            left, right = st.columns([1, 1.2])
            left.dataframe(metrics_df, width="stretch", hide_index=True)

            if {"Algorithm", "MAE", "RMSE"}.issubset(metrics_df.columns):
                chart = px.bar(
                    metrics_df,
                    x="Algorithm",
                    y=["MAE", "RMSE"],
                    barmode="group",
                    title="Forecast error comparison",
                )
                show_chart(_dark(chart), container=right)

            st.caption(result.get("message", ""))
        else:
            st.caption(
                "The estimate is based on your recent monthly income and "
                "spending history."
            )

        if st.button("Save forecast result", key="save_forecast"):
            with session_scope() as session:
                save_prediction(
                    session,
                    user_id,
                    "MONTHLY_EXPENSE_AND_SAVINGS",
                    float(result["prediction"]),
                    None,
                    str(result.get("best_model", "Unknown")),
                    {
                        "expense_metrics": result.get("metrics", []),
                        "savings_prediction": float(
                            savings_result["prediction"]
                        ),
                    },
                )
            st.success("Prediction saved to your history.")
        return

    if view == "Category insights":
        if st.session_state.get("user_role") == "ADMIN":
            with st.expander("Advanced evaluation details"):
                st.write(
                    "Several classification approaches are compared using "
                    "weighted quality scores and a confusion matrix."
                )

        if st.button(
            "Analyse category patterns",
            type="primary",
            width="stretch",
        ):
            with st.spinner("Analysing transaction descriptions..."):
                st.session_state[f"category_model_{user_id}"] = (
                    compare_category_classifiers(df, user_id)
                )

        result = st.session_state.get(f"category_model_{user_id}")
        if not result:
            st.info(
                "At least 30 labelled transactions across multiple "
                "categories are required."
            )
            return

        metrics = result.get("metrics", [])
        if not metrics:
            st.warning(
                result.get(
                    "message",
                    "Category analysis could not be completed.",
                )
            )
            return

        st.success("Category analysis completed.")
        metrics_df = pd.DataFrame(metrics)

        if st.session_state.get("user_role") == "ADMIN":
            left, right = st.columns([1.15, 0.85])
            left.dataframe(metrics_df, width="stretch", hide_index=True)

            matrix_fig = _confusion_matrix_chart(
                result.get("confusion_matrix", []),
                result.get("labels", []),
                "Category prediction quality",
            )
            if matrix_fig:
                show_chart(matrix_fig, container=right)

            if {"Algorithm", "F1 Score"}.issubset(metrics_df.columns):
                chart = px.bar(
                    metrics_df,
                    x="Algorithm",
                    y="F1 Score",
                    title="Category analysis quality comparison",
                )
                show_chart(_dark(chart, 340))

            st.caption(result.get("message", ""))
        else:
            best_score = (
                float(metrics_df["F1 Score"].max()) * 100
                if "F1 Score" in metrics_df.columns
                else 0.0
            )
            st.metric("Category analysis quality", f"{best_score:.1f}%")
            st.caption(
                "The system is ready to organise similar transaction "
                "descriptions into spending categories."
            )
        return

    if view == "Financial risk":
        if st.session_state.get("user_role") == "ADMIN":
            with st.expander("Advanced evaluation details"):
                st.write(
                    "Several classification approaches are compared for "
                    "the risk estimate."
                )

        st.warning(
            "Risk labels are educational indicators based on spending "
            "patterns. They are not proof of fraud."
        )

        if st.button(
            "Analyse financial risk",
            type="primary",
            width="stretch",
        ):
            with st.spinner("Reviewing financial risk patterns..."):
                st.session_state[f"risk_model_{user_id}"] = (
                    train_financial_risk_classifier(df, user_id)
                )

        result = st.session_state.get(f"risk_model_{user_id}")
        if not result:
            st.info("Run training after importing at least 20 transactions.")
            return

        metrics = result.get("metrics", [])
        if not metrics:
            st.warning(
                result.get(
                    "message",
                    "Financial risk analysis could not be completed.",
                )
            )
            return

        st.success("Financial risk analysis completed.")
        metrics_df = pd.DataFrame(metrics)

        if st.session_state.get("user_role") == "ADMIN":
            left, right = st.columns([1.15, 0.85])
            left.dataframe(metrics_df, width="stretch", hide_index=True)

            matrix_fig = _confusion_matrix_chart(
                result.get("confusion_matrix", []),
                result.get("labels", []),
                "Financial risk analysis quality",
            )
            if matrix_fig:
                show_chart(matrix_fig, container=right)

            st.caption(result.get("message", ""))
        else:
            best_score = (
                float(metrics_df["F1 Score"].max()) * 100
                if "F1 Score" in metrics_df.columns
                else 0.0
            )
            st.metric("Risk analysis quality", f"{best_score:.1f}%")
            st.caption(
                "The result highlights spending patterns that may need "
                "your attention."
            )
        return

    try:
        anomalies = detect_anomalies(df, user_id)
    except Exception as error:
        st.error(f"Unable to analyse unusual activity: {error}")
        return

    if anomalies is None or anomalies.empty:
        st.info("No transaction data is available for anomaly analysis.")
        return

    plot_data = _prepare_anomaly_plot_data(anomalies)
    flagged = (
        plot_data[plot_data["ml_anomaly"]]
        .sort_values("anomaly_strength", ascending=False)
        .copy()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions analysed", len(plot_data))
    c2.metric("Unusual transactions", len(flagged))
    c3.metric(
        "Anomaly rate",
        f"{len(flagged) / max(len(plot_data), 1) * 100:.1f}%",
    )

    hover_columns = {
        "anomaly_score": ":.4f",
        "anomaly_strength": ":.4f",
        "marker_size": False,
    }
    for column in (
        "description",
        "category",
        "merchant",
        "statement_label",
    ):
        if column in plot_data.columns:
            hover_columns[column] = True

    chart = px.scatter(
        plot_data,
        x="date",
        y="amount",
        color="ml_anomaly",
        symbol="ml_anomaly",
        size="marker_size",
        size_max=32,
        hover_data=hover_columns,
        title="Unusual transaction detection",
        labels={
            "ml_anomaly": "Unusual",
            "amount": "Transaction amount",
            "date": "Transaction date",
        },
    )
    chart.update_traces(
        marker=dict(
            line=dict(width=1),
            opacity=0.82,
        )
    )
    show_chart(_dark(chart, 420))

    if flagged.empty:
        st.success("No strong unusual activity was detected.")
        return

    preferred_columns = [
        "date",
        "transaction_id_masked",
        "description",
        "category",
        "amount",
        "anomaly_score",
        "statement_label",
    ]
    display_columns = [
        column
        for column in preferred_columns
        if column in flagged.columns
    ]

    st.dataframe(
        flagged[display_columns],
        width="stretch",
        hide_index=True,
    )
    st.warning(
        "An anomaly is a statistical outlier, not proof of fraud. "
        "Verify unrecognized transactions with your bank."
    )


def render_health_page(user_id: int) -> None:
    hero(
        "Financial wellness",
        "Financial health score",
        (
            "A transparent 0–100 score combines savings rate, expense "
            "stability, budget behaviour, transaction risk, and category "
            "diversification."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        st.info("Upload transactions to calculate financial health.")
        return

    score, components = calculate_health_score(df)
    left, right = st.columns([1, 1.1])

    with left:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                title={"text": "Financial Health Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "steps": [
                        {"range": [0, 40], "color": "#5a1f2a"},
                        {"range": [40, 70], "color": "#5c4a1f"},
                        {"range": [70, 100], "color": "#174b3b"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 4},
                        "value": score,
                    },
                },
            )
        )
        show_chart(_dark(fig, 390))

    with right:
        component_df = pd.DataFrame(
            {
                "Component": components.keys(),
                "Points": components.values(),
            }
        )
        chart = px.bar(
            component_df,
            x="Component",
            y="Points",
            title="Score contribution",
        )
        show_chart(_dark(chart, 390))

    if score >= 75:
        st.success(
            "Strong financial health. Maintain savings discipline and "
            "periodically review insurance, emergency reserves, and goals."
        )
    elif score >= 50:
        st.warning(
            "Moderate financial health. Focus on consistent savings and "
            "category budget adherence."
        )
    else:
        st.error(
            "Financial pressure detected. Reduce discretionary costs, "
            "verify risky transactions, and build emergency savings."
        )

    st.caption(
        "This score is an explainable educational indicator, not a credit "
        "score or lending decision."
    )


def render_advisor_page(user_id: int) -> None:
    hero(
        "Personalized guidance",
        "AI financial advisor",
        (
            "Receive explainable budget suggestions, savings actions, "
            "recurring-payment alerts, risk warnings, and an interactive "
            "expense-reduction simulator."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        st.info("Upload transactions to generate personalized advice.")
        return

    score, _ = calculate_health_score(df)
    for item in generate_advice(df, score):
        level = item.get("level", "info")
        renderer = getattr(st, level, st.info)
        renderer(
            f"**{item.get('title', 'Financial suggestion')}**\n\n"
            f"{item.get('message', '')}"
        )

    subscriptions = detect_subscription_candidates(df)
    st.subheader("Potential subscription alerts")
    if subscriptions.empty:
        st.success("No clear recurring subscription pattern detected yet.")
    else:
        st.dataframe(
            subscriptions.round(2),
            width="stretch",
            hide_index=True,
        )

    st.subheader("What-if expense reduction simulator")
    kpis = calculate_kpis(df)
    reduction = st.slider(
        "Reduce monthly expenses by",
        0,
        30,
        10,
        step=1,
        format="%d%%",
    )

    summary = monthly_summary(df)
    monthly_expense = (
        float(summary["expense"].tail(3).mean())
        if not summary.empty and "expense" in summary.columns
        else 0.0
    )
    monthly_gain = monthly_expense * reduction / 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Average monthly expense", f"₹{monthly_expense:,.0f}")
    c2.metric("Potential monthly saving", f"₹{monthly_gain:,.0f}")
    c3.metric("Potential annual saving", f"₹{monthly_gain * 12:,.0f}")

    progress_value = min(
        max((float(kpis.get("savings_rate", 0.0)) + reduction) / 40, 0.0),
        1.0,
    )
    st.progress(
        progress_value,
        text="Illustrative savings-rate improvement",
    )

    st.caption(
        "FinGuard provides educational financial guidance. It does not "
        "replace a registered adviser, tax professional, bank, or fraud "
        "investigation team."
    )


def _future_value(monthly: float, annual_rate: float, years: int) -> float:
    months = years * 12
    monthly_rate = annual_rate / 100 / 12

    if months <= 0:
        return 0.0
    if monthly_rate == 0:
        return monthly * months

    return (
        monthly
        * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        * (1 + monthly_rate)
    )


def _round_to_step(
    value: float,
    step: int,
    minimum: int,
    maximum: int,
) -> int:
    rounded = int(round(float(value) / step) * step)
    return max(minimum, min(rounded, maximum))


def render_investment_page(user_id: int) -> None:
    hero(
        "AI opportunity engine",
        "Investment ideas",
        (
            "Explore diversified educational ideas based on cash flow, "
            "savings rate, time horizon, goal, and risk preference. "
            "No product, return, or outcome is guaranteed."
        ),
    )

    df = load_user_dataframe(user_id)
    if df.empty:
        st.info(
            "Upload at least three months of transactions to unlock "
            "data-aware ideas."
        )
        return

    score, _ = calculate_health_score(df)
    monthly = monthly_summary(df)

    avg_income = (
        float(monthly["income"].tail(3).mean())
        if not monthly.empty and "income" in monthly.columns
        else 0.0
    )
    avg_expense = (
        float(monthly["expense"].tail(3).mean())
        if not monthly.empty and "expense" in monthly.columns
        else 0.0
    )
    investable = max(avg_income - avg_expense, 0.0)

    with session_scope() as session:
        saved_preferences = get_user_preferences(session, user_id)

    stored_horizon = str(
        saved_preferences.get("investment_horizon", "3-5 YEARS")
    ).upper()

    if stored_horizon in {"0-1 YEAR", "1-3 YEARS"}:
        horizon_default = "Less than 3 years"
    elif stored_horizon in {"5-10 YEARS", "10+ YEARS"}:
        horizon_default = "More than 7 years"
    else:
        horizon_default = "3–7 years"

    stored_risk = str(
        saved_preferences.get("risk_preference", "MODERATE")
    ).upper()
    risk_default = {
        "CONSERVATIVE": "Low",
        "MODERATE": "Moderate",
        "AGGRESSIVE": "High",
    }.get(stored_risk, "Moderate")

    c1, c2, c3 = st.columns(3)
    horizon_options = [
        "Less than 3 years",
        "3–7 years",
        "More than 7 years",
    ]
    horizon = c1.selectbox(
        "Investment horizon",
        horizon_options,
        index=horizon_options.index(horizon_default),
    )
    risk = c2.select_slider(
        "Risk preference",
        ["Low", "Moderate", "High"],
        value=risk_default,
    )
    goal = c3.selectbox(
        "Primary goal",
        [
            "Emergency fund",
            "Wealth creation",
            "Education",
            "Home purchase",
            "Retirement",
        ],
    )

    slider_step = 500
    raw_maximum = max(investable * 1.2, 1000)
    max_slider = max(
        int(math.ceil(raw_maximum / slider_step) * slider_step),
        1000,
    )

    saved_target = float(
        saved_preferences.get("monthly_investment_target", 0) or 0
    )
    suggested_target = (
        saved_target
        if saved_target > 0
        else investable * 0.5
    )
    default_amount = _round_to_step(
        suggested_target,
        slider_step,
        0,
        max_slider,
    )

    monthly_commitment = st.slider(
        "Monthly amount you are comfortable allocating",
        min_value=0,
        max_value=max_slider,
        value=default_amount,
        step=slider_step,
    )

    if st.button("Save these investment preferences", width="stretch"):
        risk_map = {
            "Low": "CONSERVATIVE",
            "Moderate": "MODERATE",
            "High": "AGGRESSIVE",
        }
        horizon_map = {
            "Less than 3 years": "1-3 YEARS",
            "3–7 years": "3-5 YEARS",
            "More than 7 years": "10+ YEARS",
        }

        with session_scope() as session:
            updated = get_user_preferences(session, user_id)
            updated.update(
                {
                    "risk_preference": risk_map[risk],
                    "investment_horizon": horizon_map[horizon],
                    "monthly_investment_target": monthly_commitment,
                }
            )
            save_user_preferences(session, user_id, updated)

        st.success("Investment preferences saved.")

    st.subheader("AI readiness assessment")
    a, b, c, d = st.columns(4)
    a.metric("3-month average income", f"₹{avg_income:,.0f}")
    b.metric("3-month average expense", f"₹{avg_expense:,.0f}")
    c.metric("Estimated investable surplus", f"₹{investable:,.0f}")
    d.metric("Financial health", f"{score}/100")

    if score < 50 or investable <= 0:
        st.warning(
            "Priority: stabilize cash flow, reduce expensive debt, obtain "
            "essential insurance, and build an emergency reserve before "
            "taking market risk."
        )
        allocation = pd.DataFrame(
            {
                "Idea": [
                    "Emergency reserve",
                    "Debt repayment / cash buffer",
                ],
                "Allocation": [70, 30],
            }
        )
    elif risk == "Low" or horizon == "Less than 3 years":
        allocation = pd.DataFrame(
            {
                "Idea": [
                    "Emergency reserve / liquid savings",
                    "Short-duration high-quality debt",
                    "Broad-market equity index exposure",
                ],
                "Allocation": [40, 40, 20],
            }
        )
    elif risk == "Moderate":
        allocation = pd.DataFrame(
            {
                "Idea": [
                    "Emergency reserve / liquid savings",
                    "Broad-market equity index exposure",
                    "High-quality debt allocation",
                    "Gold diversification",
                ],
                "Allocation": [20, 45, 25, 10],
            }
        )
    else:
        allocation = pd.DataFrame(
            {
                "Idea": [
                    "Emergency reserve / liquid savings",
                    "Broad-market equity index exposure",
                    "Diversified equity allocation",
                    "Debt allocation",
                    "Gold diversification",
                ],
                "Allocation": [15, 45, 25, 10, 5],
            }
        )

    allocation["Monthly illustration"] = (
        allocation["Allocation"] / 100 * monthly_commitment
    )

    left, right = st.columns([1, 1.25])
    chart = px.pie(
        allocation,
        names="Idea",
        values="Allocation",
        hole=0.48,
        title="Illustrative allocation",
    )
    show_chart(_dark(chart, 410), container=left)
    right.dataframe(
        allocation.round(0),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Contribution scenario — not a forecast")
    scenario_years = st.slider(
        "Scenario duration (years)",
        1,
        30,
        10,
    )
    assumed_rate = st.slider(
        "Illustrative annual return assumption",
        0.0,
        12.0,
        7.0,
        step=0.5,
        help=(
            "This is only a mathematical assumption, not a promise "
            "or current market forecast."
        ),
    )

    future_value = _future_value(
        float(monthly_commitment),
        float(assumed_rate),
        int(scenario_years),
    )
    invested = monthly_commitment * scenario_years * 12

    c1, c2, c3 = st.columns(3)
    c1.metric("Total contributions", f"₹{invested:,.0f}")
    c2.metric("Illustrative ending value", f"₹{future_value:,.0f}")
    c3.metric(
        "Illustrative growth",
        f"₹{max(future_value - invested, 0):,.0f}",
    )

    st.info(
        f"Goal: {goal}. Horizon: {horizon}. The allocation and "
        "contribution scenario are educational illustrations—not "
        "individualized investment advice or guaranteed returns."
    )
    st.caption(
        "Before investing, verify emergency savings, insurance, taxes, "
        "debt costs, product risks, and suitability with a registered "
        "investment adviser."
    )