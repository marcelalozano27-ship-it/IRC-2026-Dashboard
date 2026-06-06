import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="IRC Activity Planning Dashboard", layout="wide")
SHARED_PASSWORD = "lgo2026"

def check_password():
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
st.title("IRC Activity Planning Dashboard")
st.caption(
    "Decision-support dashboard for attendance trends, activity gaps, recommendations, "
    "and participant geography."
)

# --------------------------------------------------
# Load data
# --------------------------------------------------

@st.cache_data
def load_data():
    activities = pd.read_csv("data/activity_level.csv")
    public = pd.read_csv("data/public_signups.csv")
    volunteers = pd.read_csv("data/volunteer_signups.csv")
    return activities, public, volunteers


activities, public, volunteers = load_data()

# --------------------------------------------------
# Basic cleaning
# --------------------------------------------------

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
activities["event_start_date"] = pd.to_datetime(activities["event_start_date"], errors="coerce")

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
    if col in activities.columns:
        activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

public["zip"] = public["zip"].astype(str).str.extract(r"(\d{5})")[0]

# Normalize state names
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

# Attendance metrics
activities["ActualVisitors"] = activities["VisitorsRegistered"] - activities["VisitorsNoShow"]

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

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------

st.sidebar.header("Filters")

# Do not use ActivityName for main charts because it is too granular
group_col = st.sidebar.selectbox(
    "Analyze activities by",
    ["ActivitySubType", "ActivityType"],
    index=0,
)

filtered = activities.copy()

activity_types = sorted(activities["ActivityType"].dropna().unique())
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
selected_years = st.sidebar.multiselect(
    "Year",
    years,
    default=years,
)

filtered = filtered[filtered["Year"].isin(selected_years)]

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

available_months = [m for m in month_order if m in filtered["Month"].dropna().unique()]
selected_months = st.sidebar.multiselect(
    "Month",
    available_months,
    default=available_months,
)

filtered = filtered[filtered["Month"].isin(selected_months)]

days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
available_days = [d for d in days_order if d in filtered["DayOfWeek"].dropna().unique()]
selected_days = st.sidebar.multiselect(
    "Day of Week",
    available_days,
    default=available_days,
)

filtered = filtered[filtered["DayOfWeek"].isin(selected_days)]

statuses = sorted(filtered["ActivityStatus"].dropna().unique())
selected_statuses = st.sidebar.multiselect(
    "Activity Status",
    statuses,
    default=statuses,
)

filtered = filtered[filtered["ActivityStatus"].isin(selected_statuses)]

children_filter = st.sidebar.selectbox(
    "Children Included?",
    ["All", "Yes", "No"],
)

if children_filter == "Yes":
    filtered = filtered[filtered["VisitorsChildren"] > 0]
elif children_filter == "No":
    filtered = filtered[filtered["VisitorsChildren"] == 0]

min_visitors = int(activities["TotalVisitors"].min())
max_visitors = int(activities["TotalVisitors"].max())

visitor_range = st.sidebar.slider(
    "Total Visitors Range",
    min_value=min_visitors,
    max_value=max_visitors,
    value=(min_visitors, max_visitors),
)

filtered = filtered[filtered["TotalVisitors"].between(visitor_range[0], visitor_range[1])]

# Public signup data matched to filtered activities
public_filtered = public[public["ActivityID"].isin(filtered["ActivityID"])].copy()

# State filter only. City filter removed.
states = sorted(public_filtered["state_clean"].dropna().unique())
if len(states) > 0:
    selected_states = st.sidebar.multiselect(
        "Participant State",
        states,
        default=states,
    )
    public_filtered = public_filtered[public_filtered["state_clean"].isin(selected_states)]

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def safe_rate(series):
    return series.replace([np.inf, -np.inf], np.nan)


def build_scorecard(df, group_col):
    if df.empty:
        return pd.DataFrame()

    scorecard = (
        df.groupby(group_col)
        .agg(
            ActivityCount=(group_col, "count"),
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

    scorecard["SupplyScore"] = np.where(
        scorecard["ActivityCount"].max() > 0,
        scorecard["ActivityCount"] / scorecard["ActivityCount"].max(),
        0,
    )

    scorecard["DemandScore"] = np.where(
        scorecard["AvgVisitors"].max() > 0,
        scorecard["AvgVisitors"] / scorecard["AvgVisitors"].max(),
        0,
    )

    scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

    scorecard["RecommendationCategory"] = np.select(
        [
            scorecard["GapScore"] >= 0.20,
            scorecard["GapScore"] <= -0.20,
            (
                scorecard["DemandScore"] >= scorecard["DemandScore"].median()
            )
            & (
                scorecard["SupplyScore"] >= scorecard["SupplyScore"].median()
            ),
        ],
        [
            "Growth Opportunity",
            "Possible Oversaturation",
            "Core Program",
        ],
        default="Monitor",
    )

    return scorecard


def clean_chart_labels(fig, tick_angle=-35):
    fig.update_layout(
        xaxis_tickangle=tick_angle,
        legend_title_text="",
        margin=dict(l=20, r=20, t=60, b=120),
        height=520,
    )
    return fig


scorecard = build_scorecard(filtered, group_col)
# --------------------------------------------------
# Tabs
# --------------------------------------------------

tabs = st.tabs(
    [
        "Overview",
        "Question 1: Participation Drivers",
        "Question 2: Timing & Trends",
        "Question 3: Growth Opportunities",
        "Geography",
        "Volunteer Analysis",
        "Raw Data",
    ]
)

# --------------------------------------------------
# Overview
# --------------------------------------------------

with tabs[0]:
    st.subheader("Overview")

    st.markdown("""
    ### Key Questions This Dashboard Answers

    1. Which programs drive the most participation?

    2. When does participation occur and how does it change over time?

    3. Which programs are growing, declining, or showing the greatest opportunity?
    """)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Activities", f"{len(filtered):,}")
    col2.metric("Total Visitors", f"{int(filtered['TotalVisitors'].sum()):,}")
    col3.metric("Avg Visitors / Activity", f"{filtered['TotalVisitors'].mean():.1f}")
    col4.metric("No-Show Rate", f"{filtered['NoShowRate'].mean():.1%}")
    col5.metric("Volunteer Hours", f"{filtered['VolunteerHours'].sum():,.1f}")

    st.markdown("### Key Findings")

    if not scorecard.empty:
        top_frequency = scorecard.sort_values("ActivityCount", ascending=False).iloc[0]
        top_attendance = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_gap = scorecard.sort_values("GapScore", ascending=False).iloc[0]
        top_saturated = scorecard.sort_values("GapScore").iloc[0]

        st.write(
            f"- **{top_frequency['ActivityGroup']}** is offered most often with "
            f"**{int(top_frequency['ActivityCount'])} activities**."
        )
        st.write(
            f"- **{top_attendance['ActivityGroup']}** has the highest average attendance with "
            f"**{top_attendance['AvgVisitors']:.1f} visitors per activity**."
        )
        st.write(
            f"- **{top_gap['ActivityGroup']}** appears to be the strongest growth opportunity "
            f"based on demand relative to supply."
        )
        st.write(
            f"- **{top_saturated['ActivityGroup']}** may be oversupplied relative to attendance demand."
        )

    st.info(
        "Use the tabs above to move through the dashboard based on the three main client questions."
    )

# --------------------------------------------------
# Question 1: Participation Drivers
# --------------------------------------------------

with tabs[1]:
    st.subheader("Question 1: Which programs drive the most participation?")

    st.info(
        "Use this section to identify which activity types attract the highest levels of participation and demand."
    )

    if scorecard.empty:
        st.warning("No data available for current filters.")
    else:
        st.dataframe(scorecard.sort_values("AvgVisitors", ascending=False), use_container_width=True)

        st.markdown("### Top Activity Groups by Total Visitors")

        top_total = scorecard.sort_values("TotalVisitors", ascending=False).head(15)

        fig = px.bar(
            top_total,
            x="ActivityGroup",
            y="TotalVisitors",
            color="RecommendationCategory",
            title=f"Top Activity Groups by Total Visitors ({group_col})",
        )
        fig = clean_chart_labels(fig)
        st.plotly_chart(fig, use_container_width=True, key="q1_total_visitors")

        st.markdown("### Top Activity Groups by Average Visitors")

        top_avg = scorecard.sort_values("AvgVisitors", ascending=False).head(15)

        fig = px.bar(
            top_avg,
            x="ActivityGroup",
            y="AvgVisitors",
            color="RecommendationCategory",
            title=f"Top Activity Groups by Average Visitors ({group_col})",
        )
        fig = clean_chart_labels(fig)
        st.plotly_chart(fig, use_container_width=True, key="q1_avg_visitors")

# --------------------------------------------------
# Question 2: Timing & Trends
# --------------------------------------------------

with tabs[2]:
    st.subheader("Question 2: When does participation occur and how does it change over time?")

    st.info(
        "Use this section to understand yearly, monthly, and day-of-week participation patterns."
    )

    yearly_total = (
        filtered.groupby("Year")
        .agg(
            ActivityCount=("ActivityID", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            VolunteerHours=("VolunteerHours", "sum"),
        )
        .reset_index()
        .sort_values("Year")
    )

    st.markdown("### Activity Count by Year")

    fig = px.bar(
        yearly_total,
        x="Year",
        y="ActivityCount",
        color="ActivityCount",
        title="Activity Count by Year",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True, key="q2_activity_count_year")

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

    yearly_group = (
        filtered.groupby(["Year", group_col])
        .agg(
            ActivityCount=(group_col, "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            VolunteerHours=("VolunteerHours", "sum"),
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
    )

    top_groups = (
        scorecard.sort_values("TotalVisitors", ascending=False)
        .head(8)["ActivityGroup"]
        .tolist()
    )

    yearly_group_top = yearly_group[yearly_group["ActivityGroup"].isin(top_groups)]

    st.markdown("### Activity Count by Year and Top Activity Groups")

    fig = px.line(
        yearly_group_top,
        x="Year",
        y="ActivityCount",
        color="ActivityGroup",
        markers=True,
        title=f"Activity Count by Year and Top {group_col}",
    )
    fig.update_layout(height=520)
    st.plotly_chart(fig, use_container_width=True, key="q2_group_activity_count_year")

    st.markdown("### Top Activity Groups by Month")

    monthly = (
        filtered.groupby(["MonthNum", "Month", group_col])
        .agg(
            ActivityCount=(group_col, "count"),
            AvgVisitors=("TotalVisitors", "mean"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgNoShowRate=("NoShowRate", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "ActivityGroup"})
        .sort_values(["MonthNum", "AvgVisitors"], ascending=[True, False])
    )

    if monthly.empty:
        st.warning("No monthly data available for current filters.")
    else:
        best_by_month = monthly.groupby(["MonthNum", "Month"]).head(3)

        st.dataframe(best_by_month, use_container_width=True)

        fig = px.bar(
            best_by_month,
            x="Month",
            y="AvgVisitors",
            color="ActivityGroup",
            barmode="group",
            title=f"Top {group_col} by Month",
            category_orders={"Month": month_order},
        )
        fig.update_layout(height=560)
        st.plotly_chart(fig, use_container_width=True, key="q2_monthly_top_groups")

        available_months_for_select = [
            m for m in month_order if m in best_by_month["Month"].unique()
        ]

        selected_month = st.selectbox(
            "Choose a month",
            available_months_for_select,
            key="q2_month_recommendation_select",
        )

        month_recs = best_by_month[best_by_month["Month"] == selected_month]

        st.markdown(f"### Recommendations for {selected_month}")

        for _, row in month_recs.iterrows():
            st.info(
                f"**{row['ActivityGroup']}** performs well in **{selected_month}**, "
                f"averaging **{row['AvgVisitors']:.1f} visitors per activity**."
            )

    st.markdown("### Best Days of Week")

    day_summary = (
        filtered.groupby("DayOfWeek")
        .agg(
            ActivityCount=("DayOfWeek", "count"),
            AvgVisitors=("TotalVisitors", "mean"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgNoShowRate=("NoShowRate", "mean"),
        )
        .reindex(days_order)
        .dropna(how="all")
        .reset_index()
    )

    st.dataframe(day_summary, use_container_width=True)

    if not day_summary.empty:
        fig = px.bar(
            day_summary,
            x="DayOfWeek",
            y="AvgVisitors",
            color="DayOfWeek",
            title="Average Visitors by Day of Week",
            category_orders={"DayOfWeek": days_order},
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True, key="q2_day_avg_visitors")

# --------------------------------------------------
# Question 3: Growth Opportunities
# --------------------------------------------------

with tabs[3]:
    st.subheader("Question 3: Which programs are growing, declining, or showing opportunity?")

    st.markdown(
        """
        This section compares **supply** and **demand**.

        - **Supply** = number of activities offered
        - **Demand** = average visitors per activity
        - **Growth Opportunity** = high demand but lower supply
        - **Possible Oversaturation** = high supply but lower demand
        """
    )

    if scorecard.empty:
        st.warning("No data available for current filters.")
    else:
        matrix = scorecard.sort_values("GapScore", ascending=False)

        st.dataframe(matrix, use_container_width=True)

        fig = px.scatter(
            matrix,
            x="SupplyScore",
            y="DemandScore",
            size="TotalVisitors",
            color="RecommendationCategory",
            hover_name="ActivityGroup",
            title="Opportunity Matrix: Supply vs Demand",
            size_max=55,
        )
        fig.update_layout(height=560)
        st.plotly_chart(fig, use_container_width=True, key="q3_opportunity_matrix")

        st.markdown("### Recommendation Category Mix")

        rec_counts = scorecard["RecommendationCategory"].value_counts().reset_index()
        rec_counts.columns = ["RecommendationCategory", "Count"]

        fig = px.pie(
            rec_counts,
            names="RecommendationCategory",
            values="Count",
            title="Recommendation Category Mix",
            hole=0.35,
        )
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True, key="q3_recommendation_pie")

        st.markdown("### Growth Opportunities")

        growth = matrix[matrix["RecommendationCategory"] == "Growth Opportunity"]

        if growth.empty:
            st.info("No strong growth opportunities detected with current filters.")
        else:
            for _, row in growth.head(5).iterrows():
                st.success(
                    f"Consider expanding **{row['ActivityGroup']}**. "
                    f"It averages **{row['AvgVisitors']:.1f} visitors per activity** "
                    f"across **{int(row['ActivityCount'])} activities**."
                )

        st.markdown("### Possible Oversaturation")

        saturated = matrix[matrix["RecommendationCategory"] == "Possible Oversaturation"]

        if saturated.empty:
            st.info("No major oversaturation detected with current filters.")
        else:
            for _, row in saturated.head(5).iterrows():
                st.warning(
                    f"Review **{row['ActivityGroup']}** before adding more offerings. "
                    f"It has **{int(row['ActivityCount'])} activities** with "
                    f"**{row['AvgVisitors']:.1f} average visitors**."
                )
