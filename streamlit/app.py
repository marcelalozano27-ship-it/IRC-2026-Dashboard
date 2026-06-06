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
def show_question_header(question, purpose, insight_text=None):
    st.markdown(f"## {question}")
    st.info(purpose)

    if insight_text:
        st.success(f"**Key Insight:** {insight_text}")
# --------------------------------------------------
# Tabs
# --------------------------------------------------

tabs = st.tabs(
    [
        "Overview",
        "Participation Drivers",
        "Timing & Trends",
        "Growth Opportunities",
    ]
)

# --------------------------------------------------
# Overview
# --------------------------------------------------

# --------------------------------------------------
# Overview
# --------------------------------------------------

with tabs[0]:
    st.subheader("Overview")

    st.markdown("""
    This dashboard is organized around three client decision questions:

    1. **Which programs drive the most participation?**
    2. **When does participation occur and how does it change over time?**
    3. **Which programs are growing, declining, or showing opportunity?**
    """)

    col1, col2, col3, col4 = st.columns(4)

    total_activities = len(filtered)
    total_visitors = int(filtered["TotalVisitors"].sum())
    avg_visitors = filtered["TotalVisitors"].mean()
    volunteer_hours = filtered["VolunteerHours"].sum()

    col1.metric("Activities", f"{total_activities:,}")
    col2.metric("Total Visitors", f"{total_visitors:,}")
    col3.metric("Avg Visitors / Activity", f"{avg_visitors:.1f}")
    col4.metric("Volunteer Hours", f"{volunteer_hours:,.1f}")

    st.markdown("### Key Insights")

    if not scorecard.empty:
        top_total = scorecard.sort_values("TotalVisitors", ascending=False).iloc[0]
        top_avg = scorecard.sort_values("AvgVisitors", ascending=False).iloc[0]
        top_growth = scorecard.sort_values("GapScore", ascending=False).iloc[0]

        insight_col1, insight_col2, insight_col3 = st.columns(3)

        with insight_col1:
            st.success(
                f"**Highest total participation:**\n\n"
                f"{top_total['ActivityGroup']} has the most total visitors "
                f"with **{int(top_total['TotalVisitors']):,} visitors**."
            )

        with insight_col2:
            st.info(
                f"**Highest average attendance:**\n\n"
                f"{top_avg['ActivityGroup']} averages "
                f"**{top_avg['AvgVisitors']:.1f} visitors per activity**."
            )

        with insight_col3:
            st.warning(
                f"**Potential growth opportunity:**\n\n"
                f"{top_growth['ActivityGroup']} shows the strongest demand gap "
                f"based on current supply and attendance."
            )

    st.markdown("### Dashboard Flow")

    st.write(
        "Start with **Participation Drivers** to understand which programs are most used, "
        "then move to **Timing & Trends** to understand seasonality, and finish with "
        "**Growth Opportunities** to identify where IRC may want to expand or reassess programming."
    )

# --------------------------------------------------
# Question 1: Participation Drivers
# --------------------------------------------------
with tabs[1]:

    if scorecard.empty:
        st.warning("No data available for current filters.")

    else:

        top_total_insight = (
            scorecard.sort_values("TotalVisitors", ascending=False)
            .iloc[0]
        )

        show_question_header(
            "Question 1: Which programs drive the most participation?",
            "Use this section to identify which activity types attract the highest levels of participation and demand.",
            f"{top_total_insight['ActivityGroup']} has the highest total participation with "
            f"{int(top_total_insight['TotalVisitors']):,} visitors."
        )

        st.dataframe(
            scorecard.sort_values("AvgVisitors", ascending=False),
            use_container_width=True
        )

        st.markdown("### Top Activity Groups by Total Visitors")

        top_total = (
            scorecard.sort_values("TotalVisitors", ascending=False)
            .head(15)
        )

        fig = px.bar(
            top_total,
            x="ActivityGroup",
            y="TotalVisitors",
            color="RecommendationCategory",
            title=f"Top Activity Groups by Total Visitors ({group_col})",
        )

        fig = clean_chart_labels(fig)

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="q1_total_visitors"
        )

        st.markdown("### Top Activity Groups by Average Visitors")

        top_avg = (
            scorecard.sort_values("AvgVisitors", ascending=False)
            .head(15)
        )

        fig = px.bar(
            top_avg,
            x="ActivityGroup",
            y="AvgVisitors",
            color="RecommendationCategory",
            title=f"Top Activity Groups by Average Visitors ({group_col})",
        )

        fig = clean_chart_labels(fig)

        st.plotly_chart(
            fig,
            use_container_width=True,
            key="q1_avg_visitors"
        )

# --------------------------------------------------
# Question 2: Timing & Trends
# --------------------------------------------------

with tabs[2]:

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

    best_year = yearly_total.sort_values(
        "TotalVisitors",
        ascending=False
    ).iloc[0]

    show_question_header(
        "Question 2: When does participation occur and how does it change over time?",
        "Use this section to understand yearly, monthly, and day-of-week participation patterns.",
        f"{int(best_year['Year'])} had the highest participation with "
        f"{int(best_year['TotalVisitors']):,} visitors."
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

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="q2_activity_count_year"
    )
# --------------------------------------------------
# Question 3: Growth Opportunities
# --------------------------------------------------

with tabs[3]:
top_growth = scorecard.sort_values("GapScore", ascending=False).iloc[0]

show_question_header(
    "Question 3: Which programs are growing, declining, or showing opportunity?",
    "Use this section to compare supply and demand and identify where IRC may want to expand, monitor, or reassess programming.",
    f"{top_growth['ActivityGroup']} shows the strongest growth opportunity based on demand relative to supply."
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
