import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# --------------------------------------------------
# Page configuration and password protection
# --------------------------------------------------

st.set_page_config(
    page_title="IRC Activity Planning Dashboard",
    page_icon="🌿",
    layout="wide",
)

SHARED_PASSWORD = "lgo2026"
DATA_DIR = Path("data")


def check_password() -> bool:
    """Simple shared-password gate for the prototype."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("IRC Activity Planning Dashboard")
    st.caption("Please enter the shared password to access the dashboard.")

    password = st.text_input("Password", type="password")

    if password == SHARED_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()
    elif password:
        st.error("Incorrect password")

    return False


if not check_password():
    st.stop()


# --------------------------------------------------
# Utility functions
# --------------------------------------------------


def require_columns(df: pd.DataFrame, required_cols: list[str], dataset_name: str) -> None:
    """Stop the app with a clear message if required columns are missing."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(
            f"The {dataset_name} dataset is missing required columns: "
            f"{', '.join(missing)}"
        )
        st.stop()


def ensure_column(df: pd.DataFrame, col: str, default_value=0) -> pd.DataFrame:
    """Create a missing column so optional metrics do not break the dashboard."""
    if col not in df.columns:
        df[col] = default_value
    return df


def format_number(value, decimals: int = 0) -> str:
    if pd.isna(value):
        return "N/A"
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def format_percent(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def clean_chart_labels(fig, tick_angle: int = -35, height: int = 520):
    fig.update_layout(
        xaxis_tickangle=tick_angle,
        legend_title_text="",
        margin=dict(l=20, r=20, t=70, b=120),
        height=height,
    )
    return fig


def show_question_header(question: str, purpose: str, insight_text: str | None = None):
    st.markdown(f"## {question}")
    st.info(purpose)
    if insight_text:
        st.success(f"**Key Insight:** {insight_text}")


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    activities = pd.read_csv(DATA_DIR / "activity_level.csv")
    public = pd.read_csv(DATA_DIR / "public_signups.csv")
    volunteers = pd.read_csv(DATA_DIR / "volunteer_signups.csv")
    return activities, public, volunteers


# --------------------------------------------------
# Load and validate data
# --------------------------------------------------

activities, public, volunteers = load_data()

require_columns(
    activities,
    ["ActivityID", "Date", "ActivityType", "ActivitySubType", "TotalVisitors"],
    "activity_level.csv",
)

# Optional columns used in calculations and filters
optional_activity_cols = [
    "ActivityStatus",
    "Volunteers",
    "VolunteerHours",
    "Staff",
    "StaffHours",
    "VisitorsRegistered",
    "VisitorsNoShow",
    "VisitorsWalkUp",
    "VisitorsChildren",
    "VisitorsRegisteredIrvineResident",
    "VisitorsRegisteredIrvineNonResident",
    "TotalGuests",
    "public_visitor_slots",
]

for col in optional_activity_cols:
    default = "Unknown" if col == "ActivityStatus" else 0
    activities = ensure_column(activities, col, default)

public = ensure_column(public, "ActivityID", np.nan)
public = ensure_column(public, "state", "Unknown")
public = ensure_column(public, "zip", np.nan)

# --------------------------------------------------
# Cleaning and feature engineering
# --------------------------------------------------

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
if "event_start_date" in activities.columns:
    activities["event_start_date"] = pd.to_datetime(
        activities["event_start_date"], errors="coerce"
    )

activities["Year"] = activities["Date"].dt.year
activities["Month"] = activities["Date"].dt.month_name()
activities["MonthNum"] = activities["Date"].dt.month
activities["DayOfWeek"] = activities["Date"].dt.day_name()

numeric_cols = [
    "Volunteers",
    "VolunteerHours",
    "Staff",
    "StaffHours",
    "VisitorsRegistered",
    "VisitorsNoShow",
    "VisitorsWalkUp",
    "VisitorsChildren",
    "VisitorsRegisteredIrvineResident",
    "VisitorsRegisteredIrvineNonResident",
    "TotalVisitors",
    "TotalGuests",
    "public_visitor_slots",
]

for col in numeric_cols:
    activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

activities["ActualVisitors"] = (
    activities["VisitorsRegistered"] - activities["VisitorsNoShow"]
).clip(lower=0)

activities["AttendanceRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["ActualVisitors"] / activities["VisitorsRegistered"],
    np.nan,
)

activities["NoShowRate"] = np.where(
    activities["VisitorsRegistered"] > 0,
    activities["VisitorsNoShow"] / activities["VisitorsRegistered"],
    np.nan,
)

activities["FillRate"] = np.where(
    activities["public_visitor_slots"] > 0,
    activities["VisitorsRegistered"] / activities["public_visitor_slots"],
    np.nan,
)

# Prevent impossible rates from distorting visuals
for rate_col in ["AttendanceRate", "NoShowRate", "FillRate"]:
    activities[rate_col] = activities[rate_col].replace([np.inf, -np.inf], np.nan)

public["zip"] = public["zip"].astype(str).str.extract(r"(\d{5})")[0]
public["state_clean"] = public["state"].astype(str).str.strip().str.upper()

state_map = {
    "CA": "California",
    "CA.": "California",
    "CALIFORNIA": "California",
    "CALIF": "California",
    "AZ": "Arizona",
    "ARIZONA": "Arizona",
    "CO": "Colorado",
    "COLORADO": "Colorado",
    "DC": "District of Columbia",
    "DISTRICT OF COLUMBIA": "District of Columbia",
    "FL": "Florida",
    "FLORIDA": "Florida",
    "GA": "Georgia",
    "GEORGIA": "Georgia",
    "IA": "Iowa",
    "IOWA": "Iowa",
    "MA": "Massachusetts",
    "MASSACHUSETTS": "Massachusetts",
    "MI": "Michigan",
    "MICHIGAN": "Michigan",
    "MN": "Minnesota",
    "NH": "New Hampshire",
    "ND": "North Dakota",
    "OK": "Oklahoma",
    "TX": "Texas",
    "VA": "Virginia",
    "WV": "West Virginia",
}

public["state_clean"] = (
    public["state_clean"]
    .map(state_map)
    .fillna(public["state"].astype(str).str.strip().str.title())
)

month_order = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.header("Filters")
st.sidebar.caption("Use these controls to narrow the analysis shown across all tabs.")

group_options = [col for col in ["ActivitySubType", "ActivityType"] if col in activities.columns]
group_col = st.sidebar.selectbox("Analyze activities by", group_options, index=0)

filtered = activities.copy()

activity_types = sorted(filtered["ActivityType"].dropna().unique())
selected_types = st.sidebar.multiselect(
    "Activity Type",
    activity_types,
    default=activity_types,
)
filtered = filtered[filtered["ActivityType"].isin(selected_types)]

subtypes = sorted(filtered["ActivitySubType"].dropna().unique())
selected_subtypes = st.sidebar.multiselect(
    "Activity Subtype",
    subtypes,
    default=subtypes,
)
filtered = filtered[filtered["ActivitySubType"].isin(selected_subtypes)]

years = sorted(filtered["Year"].dropna().astype(int).unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)
if selected_years:
    filtered = filtered[filtered["Year"].isin(selected_years)]

available_months = [m for m in month_order if m in filtered["Month"].dropna().unique()]
selected_months = st.sidebar.multiselect(
    "Month",
    available_months,
    default=available_months,
)
if selected_months:
    filtered = filtered[filtered["Month"].isin(selected_months)]

available_days = [d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()]
selected_days = st.sidebar.multiselect(
    "Day of Week",
    available_days,
    default=available_days,
)
if selected_days:
    filtered = filtered[filtered["DayOfWeek"].isin(selected_days)]

statuses = sorted(filtered["ActivityStatus"].dropna().unique())
selected_statuses = st.sidebar.multiselect(
    "Activity Status",
    statuses,
    default=statuses,
)
if selected_statuses:
    filtered = filtered[filtered["ActivityStatus"].isin(selected_statuses)]

children_filter = st.sidebar.selectbox("Children Included?", ["All", "Yes", "No"])
if children_filter == "Yes":
    filtered = filtered[filtered["VisitorsChildren"] > 0]
elif children_filter == "No":
    filtered = filtered[filtered["VisitorsChildren"] == 0]

min_visitors = int(activities["TotalVisitors"].min())
max_visitors = int(activities["TotalVisitors"].max())
if min_visitors < max_visitors:
    visitor_range = st.sidebar.slider(
        "Total Visitors Range",
        min_value=min_visitors,
        max_value=max_visitors,
        value=(min_visitors, max_visitors),
    )
    filtered = filtered[filtered["TotalVisitors"].between(visitor_range[0], visitor_range[1])]

public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])].copy()
states = sorted(public_filtered["state_clean"].dropna().unique())
if states:
    selected_states = st.sidebar.multiselect(
        "Participant State",
        states,
        default=states,
    )
    public_filtered = public_filtered[public_filtered["state_clean"].isin(selected_states)]

st.sidebar.markdown("---")
st.sidebar.markdown("### How to use this dashboard")
st.sidebar.markdown(
    """
    1. Start with the **Overview** tab.
    2. Use **Participation Drivers** to find high-performing programs.
    3. Use **Timing & Trends** to understand seasonality.
    4. Use **Growth Opportunities** to compare supply and demand.
    """
)


# --------------------------------------------------
# Analytical scorecard
# --------------------------------------------------


def build_scorecard(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    scorecard = (
        df.groupby(group_col, dropna=True)
        .agg(
            ActivityCount=("ActivityID", "nunique"),
            TotalRows=("ActivityID", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            MedianVisitors=("TotalVisitors", "median"),
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            Children=("VisitorsChildren", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            AvgAttendanceRate=("AttendanceRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean"),
            AvgFillRate=("FillRate", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
    )

    if scorecard.empty:
        return scorecard

    max_supply = scorecard["ActivityCount"].max()
    max_demand = scorecard["AvgVisitors"].max()

    scorecard["SupplyScore"] = np.where(
        max_supply > 0,
        scorecard["ActivityCount"] / max_supply,
        0,
    )
    scorecard["DemandScore"] = np.where(
        max_demand > 0,
        scorecard["AvgVisitors"] / max_demand,
        0,
    )
    scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

    supply_med = scorecard["SupplyScore"].median()
    demand_med = scorecard["DemandScore"].median()

    scorecard["RecommendationCategory"] = np.select(
        [
            (scorecard["DemandScore"] >= demand_med) & (scorecard["SupplyScore"] < supply_med),
            (scorecard["DemandScore"] < demand_med) & (scorecard["SupplyScore"] >= supply_med),
            (scorecard["DemandScore"] >= demand_med) & (scorecard["SupplyScore"] >= supply_med),
        ],
        [
            "Growth Opportunity",
            "Possible Oversaturation",
            "Core Program",
        ],
        default="Monitor",
    )

    return scorecard.sort_values("TotalVisitors", ascending=False)


scorecard = build_scorecard(filtered, group_col)


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("IRC Activity Planning Dashboard")
st.caption(
    "Sprint 1 prototype designed to help IRC move from historical activity data "
    "to evidence-based programming decisions."
)

st.markdown(
    """
    IRC has collected over a decade of activity, participant, and volunteer data through LetsGoOutside.org. 
    This dashboard is designed as a **decision-support tool**, not simply a reporting tool. Because the final 
    dashboard requirements are still being shaped, this prototype helps define the key planning questions, 
    metrics, and recommendation framework that can guide future programming decisions.
    """
)

if filtered.empty:
    st.warning("No records match the current filter selections. Adjust the sidebar filters to continue.")
    st.stop()


# --------------------------------------------------
# Tabs
# --------------------------------------------------

tabs = st.tabs(
    [
        "Overview",
        "Participation Drivers",
        "Timing & Trends",
        "Growth Opportunities",
        "Data Quality",
    ]
)


# --------------------------------------------------
# Overview
# --------------------------------------------------

with tabs[0]:
    st.subheader("Executive Overview")

    st.markdown(
        """
        This Sprint 1 prototype is organized around three client planning questions:

        1. **Which programs drive the most participation?**
        2. **When does participation occur and how does it change over time?**
        3. **Which programs are growing, declining, or showing opportunity?**
        """
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    total_activities = filtered["ActivityID"].nunique()
    total_visitors = filtered["TotalVisitors"].sum()
    avg_visitors = filtered["TotalVisitors"].mean()
    volunteer_hours = filtered["VolunteerHours"].sum()
    avg_fill_rate = filtered["FillRate"].mean()

    col1.metric("Activities", format_number(total_activities))
    col2.metric("Total Visitors", format_number(total_visitors))
    col3.metric("Avg Visitors / Activity", format_number(avg_visitors, 1))
    col4.metric("Volunteer Hours", format_number(volunteer_hours, 1))
    col5.metric("Avg Fill Rate", format_percent(avg_fill_rate))

    st.markdown("### Initial Analytical Takeaways")

    if not scorecard.empty:
        top_total = scorecard.sort_values("TotalVisitors", ascending=False).iloc[0]
        top_avg = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_growth = scorecard.sort_values("GapScore", ascending=False).iloc[0]

        insight_col1, insight_col2, insight_col3 = st.columns(3)

        with insight_col1:
            st.success(
                f"**Highest total participation**\n\n"
                f"{top_total['ActivityGroup']} has the most total visitors "
                f"with **{format_number(top_total['TotalVisitors'])} visitors**."
            )

        with insight_col2:
            st.info(
                f"**Highest average attendance**\n\n"
                f"{top_avg['ActivityGroup']} averages "
                f"**{format_number(top_avg['AvgVisitors'], 1)} visitors per activity**."
            )

        with insight_col3:
            st.warning(
                f"**Potential growth opportunity**\n\n"
                f"{top_growth['ActivityGroup']} has the strongest demand gap "
                f"based on current supply and attendance."
            )

    st.markdown("### Strategic Contribution")
    st.markdown(
        """
        | What IRC needed | What we discovered | What this prototype delivers |
        |---|---|---|
        | A dashboard to understand historical activity data | No fully defined KPI framework or success criteria yet | A decision-support framework organized around planning questions |
        | Better visibility into participation | Multiple data sources at different levels of detail | Integrated activity-level analysis with filters and KPI cards |
        | Support for future programming decisions | Program opportunity requires comparing supply and demand | Recommendation categories for growth, monitoring, and oversaturation |
        """
    )

    st.caption(
        "Sprint 1 Prototype: recommendation logic and KPI definitions will be refined with IRC feedback in future sprints."
    )


# --------------------------------------------------
# Participation Drivers
# --------------------------------------------------

with tabs[1]:
    if scorecard.empty:
        st.warning("No data available for current filters.")
    else:
        top_total_insight = scorecard.sort_values("TotalVisitors", ascending=False).iloc[0]
        top_avg_insight = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_frequency_insight = scorecard.sort_values("ActivityCount", ascending=False).iloc[0]

        show_question_header(
            "Question 1: Which programs drive the most participation?",
            "Use this section to identify which activity groups attract the highest participation and which programs may be central to IRC engagement.",
            f"{top_total_insight['ActivityGroup']} drives the most overall participation with "
            f"{format_number(top_total_insight['TotalVisitors'])} total visitors.",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Highest Total Participation",
            str(top_total_insight["ActivityGroup"]),
            f"{format_number(top_total_insight['TotalVisitors'])} visitors",
        )
        c2.metric(
            "Highest Avg Attendance",
            str(top_avg_insight["ActivityGroup"]),
            f"{format_number(top_avg_insight['AvgVisitors'], 1)} visitors/activity",
        )
        c3.metric(
            "Most Frequently Offered",
            str(top_frequency_insight["ActivityGroup"]),
            f"{format_number(top_frequency_insight['ActivityCount'])} activities",
        )

        st.markdown("### Top Activity Groups by Total Visitors")
        top_total = scorecard.sort_values("TotalVisitors", ascending=False).head(15)
        fig = px.bar(
            top_total,
            x="ActivityGroup",
            y="TotalVisitors",
            color="RecommendationCategory",
            text="TotalVisitors",
            title=f"Top Activity Groups by Total Visitors ({group_col})",
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig = clean_chart_labels(fig)
        st.plotly_chart(fig, use_container_width=True, key="q1_total_visitors")
        st.info(
            "**Planning use:** Groups with high total visitors represent major participation drivers. "
            "These programs may deserve priority when allocating planning attention, staffing, or future investment."
        )

        st.markdown("### Average Visitors per Activity")
        top_avg = scorecard.sort_values("AvgVisitors", ascending=False).head(15)
        fig = px.bar(
            top_avg,
            x="ActivityGroup",
            y="AvgVisitors",
            color="RecommendationCategory",
            text="AvgVisitors",
            title=f"Top Activity Groups by Average Visitors ({group_col})",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig = clean_chart_labels(fig)
        st.plotly_chart(fig, use_container_width=True, key="q1_avg_visitors")
        st.info(
            "**Planning use:** Average visitors per activity helps separate broad popularity from activity frequency. "
            "A program offered less often may still show strong demand if its average attendance is high."
        )

        st.markdown("### Program Scorecard")
        display_cols = [
            "ActivityGroup",
            "RecommendationCategory",
            "ActivityCount",
            "TotalVisitors",
            "AvgVisitors",
            "AvgAttendanceRate",
            "AvgFillRate",
            "VolunteerHours",
        ]
        st.dataframe(
            scorecard[display_cols].sort_values("TotalVisitors", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# --------------------------------------------------
# Timing and Trends
# --------------------------------------------------

with tabs[2]:
    yearly_total = (
        filtered.groupby("Year", dropna=True)
        .agg(
            ActivityCount=("ActivityID", "nunique"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            VolunteerHours=("VolunteerHours", "sum"),
        )
        .reset_index()
        .sort_values("Year")
    )

    if yearly_total.empty:
        st.warning("No yearly data available for current filters.")
    else:
        best_year = yearly_total.sort_values("TotalVisitors", ascending=False).iloc[0]
        busiest_year = yearly_total.sort_values("ActivityCount", ascending=False).iloc[0]

        show_question_header(
            "Question 2: When does participation occur and how does it change over time?",
            "Use this section to understand yearly, monthly, and day-of-week participation patterns.",
            f"{int(best_year['Year'])} had the highest participation with "
            f"{format_number(best_year['TotalVisitors'])} visitors.",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Highest Participation Year", int(best_year["Year"]), f"{format_number(best_year['TotalVisitors'])} visitors")
        c2.metric("Most Active Year", int(busiest_year["Year"]), f"{format_number(busiest_year['ActivityCount'])} activities")
        c3.metric("Years in Current View", format_number(yearly_total["Year"].nunique()))

        st.markdown("### Total Visitors by Year")
        fig = px.line(
            yearly_total,
            x="Year",
            y="TotalVisitors",
            markers=True,
            title="Total Visitors by Year",
        )
        fig.update_traces(line=dict(width=4))
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True, key="q2_total_visitors_year")

        st.markdown("### Activity Count by Year")
        fig = px.bar(
            yearly_total,
            x="Year",
            y="ActivityCount",
            text="ActivityCount",
            title="Activity Count by Year",
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True, key="q2_activity_count_year")

        yearly_group = (
            filtered.groupby(["Year", group_col], dropna=True)
            .agg(
                ActivityCount=("ActivityID", "nunique"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
            )
            .reset_index()
            .rename(columns={group_col: "ActivityGroup"})
        )

        top_groups = scorecard.sort_values("TotalVisitors", ascending=False).head(8)["ActivityGroup"].tolist()
        yearly_group_top = yearly_group[yearly_group["ActivityGroup"].isin(top_groups)]

        if not yearly_group_top.empty:
            st.markdown("### Top Activity Groups Over Time")
            fig = px.line(
                yearly_group_top,
                x="Year",
                y="TotalVisitors",
                color="ActivityGroup",
                markers=True,
                title=f"Total Visitors by Year for Top {group_col} Groups",
            )
            fig.update_layout(height=520)
            st.plotly_chart(fig, use_container_width=True, key="q2_group_visitors_year")

        monthly = (
            filtered.groupby(["MonthNum", "Month"], dropna=True)
            .agg(
                ActivityCount=("ActivityID", "nunique"),
                AvgVisitors=("TotalVisitors", "mean"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgNoShowRate=("NoShowRate", "mean"),
            )
            .reset_index()
            .sort_values("MonthNum")
        )

        if not monthly.empty:
            best_month = monthly.sort_values("AvgVisitors", ascending=False).iloc[0]
            st.success(
                f"**Seasonality insight:** {best_month['Month']} has the highest average attendance "
                f"with {format_number(best_month['AvgVisitors'], 1)} visitors per activity."
            )

            st.markdown("### Average Visitors by Month")
            fig = px.bar(
                monthly,
                x="Month",
                y="AvgVisitors",
                text="AvgVisitors",
                title="Average Visitors by Month",
                category_orders={"Month": month_order},
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True, key="q2_month_avg_visitors")

        day_summary = (
            filtered.groupby("DayOfWeek", dropna=True)
            .agg(
                ActivityCount=("ActivityID", "nunique"),
                AvgVisitors=("TotalVisitors", "mean"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgNoShowRate=("NoShowRate", "mean"),
            )
            .reindex(days_order)
            .dropna(how="all")
            .reset_index()
        )

        if not day_summary.empty:
            best_day = day_summary.sort_values("AvgVisitors", ascending=False).iloc[0]
            st.success(
                f"**Day-of-week insight:** {best_day['DayOfWeek']} has the highest average attendance "
                f"with {format_number(best_day['AvgVisitors'], 1)} visitors per activity."
            )
            fig = px.bar(
                day_summary,
                x="DayOfWeek",
                y="AvgVisitors",
                text="AvgVisitors",
                title="Average Visitors by Day of Week",
                category_orders={"DayOfWeek": days_order},
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True, key="q2_day_avg_visitors")


# --------------------------------------------------
# Growth Opportunities
# --------------------------------------------------

with tabs[3]:
    if scorecard.empty:
        st.warning("No data available for current filters.")
    else:
        matrix = scorecard.sort_values("GapScore", ascending=False)
        top_growth = matrix.iloc[0]
        top_saturated = matrix.sort_values("GapScore", ascending=True).iloc[0]

        show_question_header(
            "Question 3: Which programs are growing, declining, or showing opportunity?",
            "Use this section to compare program supply and participant demand to identify where IRC may want to expand, monitor, or reassess programming.",
            f"{top_growth['ActivityGroup']} shows the strongest opportunity based on demand relative to supply.",
        )

        st.markdown("### Recommendation Logic")
        st.markdown(
            """
            | Supply | Demand | Recommendation |
            |---|---|---|
            | Low | High | Growth Opportunity |
            | High | Low | Possible Oversaturation |
            | High | High | Core Program |
            | Low | Low | Monitor |
            """
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Strongest Growth Opportunity", str(top_growth["ActivityGroup"]), f"Gap score: {top_growth['GapScore']:.2f}")
        c2.metric("Possible Oversaturation", str(top_saturated["ActivityGroup"]), f"Gap score: {top_saturated['GapScore']:.2f}")
        c3.metric("Groups Evaluated", format_number(len(matrix)))

        fig = px.scatter(
            matrix,
            x="SupplyScore",
            y="DemandScore",
            size="TotalVisitors",
            color="RecommendationCategory",
            hover_name="ActivityGroup",
            hover_data={
                "ActivityCount": True,
                "AvgVisitors": ":.1f",
                "TotalVisitors": ":,.0f",
                "SupplyScore": ":.2f",
                "DemandScore": ":.2f",
                "GapScore": ":.2f",
            },
            title="Opportunity Matrix: Supply vs Demand",
            size_max=55,
        )
        fig.add_shape(type="line", x0=matrix["SupplyScore"].median(), x1=matrix["SupplyScore"].median(), y0=0, y1=1, line=dict(dash="dash"))
        fig.add_shape(type="line", x0=0, x1=1, y0=matrix["DemandScore"].median(), y1=matrix["DemandScore"].median(), line=dict(dash="dash"))
        fig.update_layout(height=590, xaxis_title="Supply Score: Relative Activity Count", yaxis_title="Demand Score: Relative Avg Visitors")
        st.plotly_chart(fig, use_container_width=True, key="q3_opportunity_matrix")

        st.info(
            "**Interpretation:** Points higher on the chart have stronger average participation. "
            "Points farther right are offered more frequently. The upper-left area is most useful for identifying potential expansion opportunities."
        )

        st.markdown("### Suggested Planning Actions")
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            st.markdown("#### Growth Opportunities")
            growth = matrix[matrix["RecommendationCategory"] == "Growth Opportunity"].sort_values("GapScore", ascending=False)
            if growth.empty:
                st.info("No strong growth opportunities detected with current filters.")
            else:
                for _, row in growth.head(5).iterrows():
                    st.success(
                        f"Consider expanding **{row['ActivityGroup']}**. "
                        f"It averages **{format_number(row['AvgVisitors'], 1)} visitors per activity** "
                        f"across **{format_number(row['ActivityCount'])} activities**."
                    )

        with action_col2:
            st.markdown("#### Possible Oversaturation")
            saturated = matrix[matrix["RecommendationCategory"] == "Possible Oversaturation"].sort_values("GapScore")
            if saturated.empty:
                st.info("No major oversaturation detected with current filters.")
            else:
                for _, row in saturated.head(5).iterrows():
                    st.warning(
                        f"Review **{row['ActivityGroup']}** before adding more offerings. "
                        f"It has **{format_number(row['ActivityCount'])} activities** with "
                        f"**{format_number(row['AvgVisitors'], 1)} average visitors**."
                    )

        st.markdown("### Full Recommendation Table")
        rec_cols = [
            "ActivityGroup",
            "RecommendationCategory",
            "ActivityCount",
            "TotalVisitors",
            "AvgVisitors",
            "SupplyScore",
            "DemandScore",
            "GapScore",
        ]
        st.dataframe(
            matrix[rec_cols].sort_values(["RecommendationCategory", "GapScore"], ascending=[True, False]),
            use_container_width=True,
            hide_index=True,
        )


# --------------------------------------------------
# Data Quality
# --------------------------------------------------

with tabs[4]:
    st.subheader("Data Quality and Sprint 1 Assumptions")

    st.markdown(
        """
        This tab is included to make the prototype transparent. The dashboard is currently a Sprint 1 analytical prototype, so the purpose is to show the direction of the analysis while identifying areas that need validation with IRC.
        """
    )

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Activity Rows", format_number(len(activities)))
    q2.metric("Filtered Rows", format_number(len(filtered)))
    q3.metric("Public Signup Rows", format_number(len(public)))
    q4.metric("Volunteer Signup Rows", format_number(len(volunteers)))

    st.markdown("### Missing Values in Key Fields")
    key_fields = ["ActivityID", "Date", "ActivityType", "ActivitySubType", "TotalVisitors", "VisitorsRegistered", "public_visitor_slots"]
    missing_summary = (
        activities[key_fields]
        .isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "Field", 0: "Missing Values"})
    )
    missing_summary["Missing Percent"] = missing_summary["Missing Values"] / len(activities)
    st.dataframe(missing_summary, use_container_width=True, hide_index=True)

    st.markdown("### Known Sprint 1 Limitations")
    st.markdown(
        """
        * Recommendation categories are preliminary and should be validated with IRC stakeholders.
        * Supply is currently measured using activity count, while demand is measured using average visitors per activity.
        * Future sprints should refine the definition of program success and determine how volunteer capacity should influence recommendations.
        * Historical naming inconsistencies may affect activity subtype comparisons.
        * Geographic analysis is included as a future enhancement once ZIP and participant location fields are validated.
        """
    )


# --------------------------------------------------
# Footer
# --------------------------------------------------

st.markdown("---")
st.caption(
    "IRC Activity Planning Dashboard | Sprint 1 Prototype | Built for exploratory analysis, client feedback, and decision-support framework validation."
)
