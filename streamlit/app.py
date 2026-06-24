import html
import re

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="IRC Program Performance & Activity Planning Dashboard",
    layout="wide"
)

SHARED_PASSWORD = "lgo2026"


def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("IRC Program Performance & Activity Planning Dashboard")
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


@st.cache_data
def load_data():
    return pd.read_csv("data/activity_level.csv")


activities = load_data()


def ensure_column(df, column, default_value):
    if column not in df.columns:
        df[column] = default_value
    return df


def pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def clean_fig(fig, height=500):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=80),
        legend_title_text="",
    )
    return fig


def select_all_multiselect(label, options, key, default_select_all=True):
    options = list(options)
    selected = st.sidebar.multiselect(
        label,
        options,
        default=options if default_select_all else [],
        key=key
    )
    return selected


def normalize_activity_text(name):
    text = html.unescape(str(name)).lower()

    replacements = {
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "â€“": "-",
        "â€”": "-",
        "&amp;": "&",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"(?i)cancelled:|canceled:", "", text)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\b\d{1,2}\s*(am|pm)\b", "", text)
    text = re.sub(r"\b20\d{2}\b", "", text)
    text = re.sub(r"\brth-[a-z0-9\-]+", "", text)
    text = re.sub(r"\brtn-[a-z0-9\-]+", "", text)
    text = re.sub(r"\bpef-[a-z0-9\-]+", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9\s&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def create_sub_activity_type(row):
    text = normalize_activity_text(row["ActivityName"])
    activity_type = str(row["ActivityType"]).lower()

    if not text:
        return "Needs Review"

    if activity_type == "hiking & fitness":
        return "Hikes"

    if activity_type == "fire watch":
        return "Fire Watch"

    if activity_type == "mountain biking":
        return "Mountain Biking"

    if activity_type == "equestrian":
        return "Equestrian Programs"

    if "trail running" in text or "trail run" in text:
        return "Trail Running"

    if any(word in text for word in [
        "hike", "hiking", "trek", "walk", "moonlight", "sunset",
        "tour", "canyon", "trail assessment", "patrol", "sinks",
        "vistas", "portola", "weir", "fremont", "mini moab"
    ]):
        return "Hikes"

    if "zumba" in text:
        return "Zumba"

    if any(word in text for word in ["yoga", "tai chi", "meditative", "meditation", "wellness"]):
        return "Yoga / Wellness"

    if any(word in text for word in ["bike", "biking"]):
        return "Mountain Biking"

    if any(word in text for word in ["equestrian", "horse"]):
        return "Equestrian Programs"

    if "wilderness access day" in text:
        return "Wilderness Access Days"

    if "friends family day" in text or "friends and family day" in text:
        return "Friends & Family Days"

    if any(word in text for word in [
        "native seed farm", "seed processing", "seed collection", "harvest",
        "growing together", "farm steward"
    ]):
        return "Native Seed Farm"

    if "native plant nursery" in text or "plant nursery" in text:
        return "Native Plant Nursery"

    if any(word in text for word in ["watering", "water trough", "plant care"]):
        return "Watering / Plant Care"

    if any(word in text for word in ["invasive", "restoration", "weed", "open space invaders", "habitat"]):
        return "Habitat Restoration"

    if "trail crew" in text or "trail work" in text or "trail maintenance" in text:
        return "Trail Crew / Trail Work"

    if "camera" in text or "science camera" in text:
        return "Camera Monitoring"

    if "bird" in text:
        return "Birding / Bird Monitoring"

    if "butterfly" in text or "butterflies" in text or "bugs" in text:
        return "Bugs & Butterflies"

    if "raptor" in text:
        return "Raptor Monitoring"

    if any(word in text for word in ["wildlife", "animal", "tracking"]):
        return "Wildlife / Animal Programs"

    if any(word in text for word in ["training", "orientation", "workshop", "cpr", "first aid"]):
        return "Training / Workshops"

    if "exploration day" in text:
        return "Exploration Days"

    if any(word in text for word in ["nature in your backyard", "nature education"]):
        return "Nature Education"

    if "volunteer" in text:
        return "Volunteer Programs"

    if "family" in text:
        return "Family Programs"

    if "camp" in text:
        return "Camps"

    if "photography" in text or "photo" in text:
        return "Photography"

    if "star" in text or "astronomy" in text:
        return "Astronomy"

    return "Needs Review"


def build_scorecard(df, group_col="SubActivityType"):
    if df.empty:
        return pd.DataFrame()

    scorecard = (
        df.groupby(group_col)
        .agg(
            ActivityCount=("ActivityID", "count"),
            TotalVisitors=("TotalVisitors", "sum"),
            AvgVisitors=("TotalVisitors", "mean"),
            MedianVisitors=("TotalVisitors", "median"),
            Registered=("VisitorsRegistered", "sum"),
            NoShows=("VisitorsNoShow", "sum"),
            WalkUps=("VisitorsWalkUp", "sum"),
            YouthParticipants=("VisitorsChildren", "sum"),
            VolunteerHours=("VolunteerHours", "sum"),
            AvgVolunteers=("Volunteers", "mean"),
            AvgFillRate=("FillRate", "mean"),
            AvgNoShowRate=("NoShowRate", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "SubActivityType"})
    )

    scorecard["SupplyScore"] = scorecard["ActivityCount"] / scorecard["ActivityCount"].max()
    scorecard["DemandScore"] = scorecard["AvgVisitors"] / scorecard["AvgVisitors"].max()
    scorecard["GapScore"] = scorecard["DemandScore"] - scorecard["SupplyScore"]

    scorecard["RecommendationCategory"] = np.select(
        [
            scorecard["GapScore"] >= 0.20,
            scorecard["GapScore"] <= -0.20,
            (scorecard["DemandScore"] >= scorecard["DemandScore"].median())
            & (scorecard["SupplyScore"] >= scorecard["SupplyScore"].median()),
        ],
        ["Expansion Opportunity", "Review Supply", "Core Program"],
        default="Monitor",
    )

    scorecard.loc[
        scorecard["SubActivityType"].eq("Needs Review"),
        "RecommendationCategory"
    ] = "Needs Review"

    return scorecard.sort_values("TotalVisitors", ascending=False)


required_columns = {
    "ActivityID": "",
    "Date": "",
    "ActivityType": "Unknown",
    "ActivitySubType": "Unknown",
    "ActivityName": "Unknown Activity",
    "Organization": "Unknown",
    "ActivityStatus": "Unknown",
    "Volunteers": 0,
    "VolunteerHours": 0,
    "Staff": 0,
    "StaffHours": 0,
    "VisitorsRegistered": 0,
    "VisitorsNoShow": 0,
    "VisitorsWalkUp": 0,
    "VisitorsChildren": 0,
    "TotalVisitors": 0,
    "TotalGuests": 0,
    "public_visitor_slots": 0,
    "Duration": 0,
}

for col, default in required_columns.items():
    activities = ensure_column(activities, col, default)

activities["Date"] = pd.to_datetime(activities["Date"], errors="coerce")
activities["Year"] = activities["Date"].dt.year
activities["Month"] = activities["Date"].dt.month_name()
activities["MonthNum"] = activities["Date"].dt.month
activities["DayOfWeek"] = activities["Date"].dt.day_name()

numeric_cols = [
    "Volunteers", "VolunteerHours", "Staff", "StaffHours",
    "VisitorsRegistered", "VisitorsNoShow", "VisitorsWalkUp",
    "VisitorsChildren", "TotalVisitors", "TotalGuests",
    "public_visitor_slots", "Duration",
]

for col in numeric_cols:
    activities[col] = pd.to_numeric(activities[col], errors="coerce").fillna(0)

for col in ["ActivityType", "ActivitySubType", "ActivityName", "Organization", "ActivityStatus"]:
    activities[col] = activities[col].astype(str).replace("nan", "Unknown").fillna("Unknown")

cancelled_mask = (
    activities["ActivityName"].str.contains("cancelled|canceled|cancel", case=False, na=False)
    | activities["ActivityStatus"].str.contains("cancelled|canceled|cancel", case=False, na=False)
)

activities = activities[~cancelled_mask].copy()
activities["SubActivityType"] = activities.apply(create_sub_activity_type, axis=1)

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


month_order = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


st.title("IRC Program Performance & Activity Planning Dashboard")
st.caption("Executive reporting and planning support powered by historical activity patterns.")

st.markdown("""
This dashboard is organized into two views: an **Executive Dashboard** to summarize IRC's overall program impact, 
and an **Activity Planning Dashboard** to help evaluate proposed activities using historical performance patterns.
""")


st.sidebar.header("Global Filters")
st.sidebar.caption("These filters apply to the Executive Dashboard only.")

exec_filtered = activities.copy()

years = sorted(exec_filtered["Year"].dropna().astype(int).unique())
selected_years = select_all_multiselect("Year", years, key="global_year_filter")
exec_filtered = exec_filtered[exec_filtered["Year"].isin(selected_years)]

activity_types = sorted(exec_filtered["ActivityType"].dropna().unique())
selected_activity_types = select_all_multiselect("Activity Type", activity_types, key="global_activity_type_filter")
exec_filtered = exec_filtered[exec_filtered["ActivityType"].isin(selected_activity_types)]

sub_activity_types = sorted(exec_filtered["SubActivityType"].dropna().unique())
selected_sub_activity_types = select_all_multiselect("Sub Activity Type", sub_activity_types, key="global_sub_activity_type_filter")
exec_filtered = exec_filtered[exec_filtered["SubActivityType"].isin(selected_sub_activity_types)]

with st.sidebar.expander("Additional Filters", expanded=False):
    available_months = [m for m in month_order if m in exec_filtered["Month"].dropna().unique()]
    selected_months = select_all_multiselect("Month", available_months, key="global_month_filter")
    exec_filtered = exec_filtered[exec_filtered["Month"].isin(selected_months)]

    available_days = [d for d in days_order if d in exec_filtered["DayOfWeek"].dropna().unique()]
    selected_days = select_all_multiselect("Day of Week", available_days, key="global_day_filter")
    exec_filtered = exec_filtered[exec_filtered["DayOfWeek"].isin(selected_days)]

    family_youth_global = st.sidebar.selectbox(
        "Family / Youth Participation",
        ["All", "Historically included children", "No recorded child participation"],
        key="global_family_youth_filter"
    )

    if family_youth_global == "Historically included children":
        exec_filtered = exec_filtered[exec_filtered["VisitorsChildren"] > 0]
    elif family_youth_global == "No recorded child participation":
        exec_filtered = exec_filtered[exec_filtered["VisitorsChildren"] == 0]


scorecard = build_scorecard(exec_filtered)

tabs = st.tabs(["Executive Dashboard", "Activity Planning Dashboard", "Data Review"])


with tabs[0]:
    filtered = exec_filtered

    st.header("Executive Dashboard")
    st.caption("A high-level view of what IRC accomplished.")

    if filtered.empty:
        st.warning("No data available for the selected filters.")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Activities", f"{len(filtered):,}")
        col2.metric("Total Visitors", f"{filtered['TotalVisitors'].sum():,.0f}")
        col3.metric("Avg Visitors / Activity", f"{filtered['TotalVisitors'].mean():.1f}")
        col4.metric("Volunteer Hours", f"{filtered['VolunteerHours'].sum():,.1f}")
        col5.metric("Youth / Family Participants", f"{filtered['VisitorsChildren'].sum():,.0f}")

        st.subheader("Executive Summary")

        top_type = filtered.groupby("ActivityType").agg(TotalVisitors=("TotalVisitors", "sum")).reset_index().sort_values("TotalVisitors", ascending=False).head(1)

        top_subtype = (
            filtered[filtered["SubActivityType"] != "Needs Review"]
            .groupby("SubActivityType")
            .agg(TotalVisitors=("TotalVisitors", "sum"))
            .reset_index()
            .sort_values("TotalVisitors", ascending=False)
            .head(1)
        )

        if not top_type.empty and not top_subtype.empty:
            st.info(
                f"IRC hosted **{len(filtered):,} activities**, reaching **{filtered['TotalVisitors'].sum():,.0f} visitors** "
                f"and generating **{filtered['VolunteerHours'].sum():,.1f} volunteer hours**. "
                f"The highest-attendance activity type was **{top_type.iloc[0]['ActivityType']}**, "
                f"and the highest-attendance sub activity type was **{top_subtype.iloc[0]['SubActivityType']}**."
            )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Activities by Activity Type")
            type_activity = filtered.groupby("ActivityType").agg(Activities=("ActivityID", "count")).reset_index().sort_values("Activities", ascending=True).tail(12)
            fig = px.bar(type_activity, x="Activities", y="ActivityType", orientation="h", title="Number of Activities by Activity Type")
            fig.update_xaxes(title="Number of Activities")
            fig.update_yaxes(title="Activity Type")
            st.plotly_chart(clean_fig(fig, 500), use_container_width=True)

        with col2:
            st.subheader("Visitors by Activity Type")
            type_visitors = filtered.groupby("ActivityType").agg(TotalVisitors=("TotalVisitors", "sum")).reset_index().sort_values("TotalVisitors", ascending=True).tail(12)
            fig = px.bar(type_visitors, x="TotalVisitors", y="ActivityType", orientation="h", title="Total Visitors by Activity Type")
            fig.update_xaxes(title="Total Visitors")
            fig.update_yaxes(title="Activity Type")
            st.plotly_chart(clean_fig(fig, 500), use_container_width=True)

        st.subheader("Sub Activity Type Performance")

        if scorecard.empty:
            st.info("No sub activity type data available.")
        else:
            subtype_chart = scorecard.sort_values("TotalVisitors", ascending=True).tail(12)
            fig = px.bar(subtype_chart, x="TotalVisitors", y="SubActivityType", color="RecommendationCategory", orientation="h", title="Top Sub Activity Types by Total Visitors")
            fig.update_xaxes(title="Total Visitors")
            fig.update_yaxes(title="Sub Activity Type")
            st.plotly_chart(clean_fig(fig, 550), use_container_width=True)

            subtype_table = scorecard[[
                "SubActivityType", "RecommendationCategory", "ActivityCount",
                "TotalVisitors", "AvgVisitors", "VolunteerHours",
                "YouthParticipants", "AvgFillRate", "AvgNoShowRate"
            ]].copy()

            subtype_table = subtype_table.rename(columns={
                "SubActivityType": "Sub Activity Type",
                "RecommendationCategory": "Recommendation",
                "ActivityCount": "Activities",
                "TotalVisitors": "Total Visitors",
                "AvgVisitors": "Avg Visitors",
                "VolunteerHours": "Volunteer Hours",
                "YouthParticipants": "Youth / Family Participants",
                "AvgFillRate": "Fill Rate",
                "AvgNoShowRate": "No Show Rate",
            })

            subtype_table["Avg Visitors"] = subtype_table["Avg Visitors"].round(1)
            subtype_table["Volunteer Hours"] = subtype_table["Volunteer Hours"].round(1)
            subtype_table["Fill Rate"] = subtype_table["Fill Rate"].map(pct)
            subtype_table["No Show Rate"] = subtype_table["No Show Rate"].map(pct)

            st.dataframe(subtype_table, use_container_width=True, hide_index=True)


with tabs[1]:
    st.header("Activity Planning Dashboard")
    st.caption("Build a proposed activity scenario using historical performance patterns.")

    st.subheader("Proposed Activity Scenario")

    planning_base = activities.copy()

    c1, c2 = st.columns(2)

    with c1:
        planning_activity_type = st.selectbox(
            "Activity Type",
            ["Select an activity type"] + sorted(planning_base["ActivityType"].dropna().unique().tolist()),
            key="planning_activity_type_single"
        )

    if planning_activity_type != "Select an activity type":
        subtype_options = sorted(
            planning_base[planning_base["ActivityType"] == planning_activity_type]["SubActivityType"].dropna().unique().tolist()
        )
    else:
        subtype_options = []

    with c2:
        planning_subtype = st.selectbox(
            "Sub Activity Type",
            ["Select a sub activity type"] + subtype_options,
            key="planning_subtype_single"
        )

    c3, c4 = st.columns(2)

    with c3:
        planning_month = st.selectbox(
            "Month",
            ["Select a month"] + month_order,
            key="planning_month_single"
        )

    with c4:
        planning_day = st.selectbox(
            "Day of Week",
            ["Select a day"] + days_order,
            key="planning_day_single"
        )

    family_youth_filter = st.selectbox(
        "Family / Youth Participation",
        ["All", "Historically included children", "No recorded child participation"],
        key="planning_family_youth_single"
    )

    scenario_ready = (
        planning_activity_type != "Select an activity type"
        and planning_subtype != "Select a sub activity type"
        and planning_month != "Select a month"
        and planning_day != "Select a day"
    )

    if not scenario_ready:
        st.info("Select an activity type, sub activity type, month, and day of week to generate a planning summary.")
    else:
        comparable = planning_base.copy()

        comparable = comparable[comparable["ActivityType"] == planning_activity_type]
        comparable = comparable[comparable["SubActivityType"] == planning_subtype]
        comparable = comparable[comparable["Month"] == planning_month]
        comparable = comparable[comparable["DayOfWeek"] == planning_day]

        if family_youth_filter == "Historically included children":
            comparable = comparable[comparable["VisitorsChildren"] > 0]
        elif family_youth_filter == "No recorded child participation":
            comparable = comparable[comparable["VisitorsChildren"] == 0]

        st.subheader("Performance Based on Similar Past Activities")

        if comparable.empty:
            st.warning("No exact match found. Showing closest historical matches instead.")

            suggestion_df = planning_base.copy()
            suggestion_df = suggestion_df[suggestion_df["ActivityType"] == planning_activity_type]
            suggestion_df = suggestion_df[suggestion_df["SubActivityType"] == planning_subtype]

            if family_youth_filter == "Historically included children":
                suggestion_df = suggestion_df[suggestion_df["VisitorsChildren"] > 0]
            elif family_youth_filter == "No recorded child participation":
                suggestion_df = suggestion_df[suggestion_df["VisitorsChildren"] == 0]

            if suggestion_df.empty:
                st.info("No past activities match this activity type and sub activity type. Try selecting a broader activity type.")
            else:
                closest_summary = (
                    suggestion_df.groupby(["Month", "DayOfWeek"])
                    .agg(
                        SimilarActivities=("ActivityID", "count"),
                        AvgVisitors=("TotalVisitors", "mean"),
                        AvgVolunteers=("Volunteers", "mean"),
                        AvgYouthFamily=("VisitorsChildren", "mean"),
                    )
                    .reset_index()
                    .sort_values("AvgVisitors", ascending=False)
                )

                st.subheader("Suggested Timing Based on Similar Activities")

                display_summary = closest_summary.head(10).rename(columns={
                    "DayOfWeek": "Day of Week",
                    "AvgVisitors": "Avg Visitors",
                    "AvgVolunteers": "Avg Volunteers",
                    "AvgYouthFamily": "Avg Youth / Family Participants",
                })

                display_summary["Avg Visitors"] = display_summary["Avg Visitors"].round(1)
                display_summary["Avg Volunteers"] = display_summary["Avg Volunteers"].round(1)
                display_summary["Avg Youth / Family Participants"] = display_summary["Avg Youth / Family Participants"].round(1)

                st.dataframe(display_summary, use_container_width=True, hide_index=True)

                best_match = closest_summary.head(1).iloc[0]

                st.info(
                    f"Best historical option: **{best_match['DayOfWeek']} in {best_match['Month']}** "
                    f"with an average of **{best_match['AvgVisitors']:.1f} visitors** "
                    f"across **{best_match['SimilarActivities']:.0f} similar activities**."
                )

                st.subheader("Top Historical Examples")

                top_examples = suggestion_df.sort_values("TotalVisitors", ascending=False).head(10)

                example_table = top_examples[[
                    "ActivityName", "Month", "DayOfWeek", "TotalVisitors",
                    "VisitorsChildren", "Volunteers", "VolunteerHours"
                ]].copy()

                example_table = example_table.rename(columns={
                    "ActivityName": "Activity Name",
                    "DayOfWeek": "Day",
                    "TotalVisitors": "Total Visitors",
                    "VisitorsChildren": "Youth / Family Participants",
                    "VolunteerHours": "Volunteer Hours",
                })

                st.dataframe(example_table, use_container_width=True, hide_index=True)

        else:
            overall_avg = planning_base["TotalVisitors"].mean()
            scenario_avg = comparable["TotalVisitors"].mean()

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Similar Past Activities", f"{len(comparable):,}")
            col2.metric("Avg Visitors", f"{scenario_avg:.1f}")
            col3.metric("Avg Volunteers", f"{comparable['Volunteers'].mean():.1f}")
            col4.metric("Avg Youth / Family Participants", f"{comparable['VisitorsChildren'].mean():.1f}")

            if scenario_avg > overall_avg:
                st.success(
                    f"Similar activities performed **above the historical average** "
                    f"({scenario_avg:.1f} vs. {overall_avg:.1f} visitors per activity)."
                )
            elif scenario_avg < overall_avg:
                st.warning(
                    f"Similar activities performed **below the historical average** "
                    f"({scenario_avg:.1f} vs. {overall_avg:.1f} visitors per activity)."
                )
            else:
                st.info("This scenario performs close to the historical average.")

            st.subheader("Similar Past Activities")

            similar_table = comparable[[
                "Date", "ActivityName", "ActivityType", "SubActivityType",
                "Organization", "DayOfWeek", "Month", "TotalVisitors",
                "VisitorsChildren", "Volunteers", "VolunteerHours"
            ]].copy()

            similar_table = similar_table.sort_values("TotalVisitors", ascending=False)

            similar_table = similar_table.rename(columns={
                "ActivityName": "Activity Name",
                "ActivityType": "Activity Type",
                "SubActivityType": "Sub Activity Type",
                "DayOfWeek": "Day",
                "TotalVisitors": "Total Visitors",
                "VisitorsChildren": "Youth / Family Participants",
                "VolunteerHours": "Volunteer Hours",
            })

            st.dataframe(similar_table.head(25), use_container_width=True, hide_index=True)

            st.subheader("Planning Summary")

            st.markdown(f"""
- Proposed activity type: **{planning_activity_type}**
- Proposed sub activity type: **{planning_subtype}**
- Proposed timing: **{planning_day} in {planning_month}**
- Expected average attendance: **{scenario_avg:.1f} visitors**
- Expected average volunteer need: **{comparable['Volunteers'].mean():.1f} volunteers**
- Expected youth/family participation: **{comparable['VisitorsChildren'].mean():.1f} participants**
""")


with tabs[2]:
    st.header("Data Review")
    st.caption("Review activities that could not be confidently mapped to a sub activity type.")

    review_df = activities[activities["SubActivityType"] == "Needs Review"].copy()

    if review_df.empty:
        st.success("No activities currently require review.")
    else:
        st.info(
            f"{len(review_df):,} activities are currently marked as **Needs Review**. "
            "These should be reviewed before finalizing sub activity reporting."
        )

        review_summary = (
            review_df.groupby(["ActivityType", "ActivityName"])
            .agg(
                Activities=("ActivityID", "count"),
                TotalVisitors=("TotalVisitors", "sum"),
                AvgVisitors=("TotalVisitors", "mean"),
            )
            .reset_index()
            .sort_values("Activities", ascending=False)
        )

        st.dataframe(review_summary.head(100), use_container_width=True, hide_index=True)
