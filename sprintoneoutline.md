# IRC Capstone Project
## Sprint 1 Review (June 12, 2026)

### Team
- Marcela Lozano (Project Lead / Technical Lead)
- Fong (Client Liaison)
- Brandon (Presentation Lead)

# Slide 1: Project Overview

## Problem Statement

Irvine Ranch Conservancy collects substantial activity, attendance, volunteer, and participant data, but the information is not currently organized into a decision-support tool that supports strategic activity planning.

As a result, IRC has limited visibility into:
- Which activities generate the strongest attendance
- Which activity types may be oversaturated
- Which activities represent growth opportunities
- Which months and days perform best
- Where participants are coming from geographically
- How volunteer-submitted activity ideas align with participant demand

# Slide 2: Project Goal

## Objective

Develop an interactive dashboard and recommendation framework that helps IRC:
- Evaluate activity performance
- Identify programming gaps
- Support stakeholder reporting
- Improve activity planning decisions
- Understand participant geography
- Analyze attendance and no-show behavior

# Slide 3: Success Criteria

### Activity Planning
- Compare attendance across activity types
- Identify potential oversaturation
- Identify growth opportunities

### Attendance Insights
- Measure attendance trends
- Track registration behavior
- Analyze no-show rates

### Geographic Analysis
- Identify where participants are coming from
- Distinguish local versus regional participation

### Stakeholder Reporting
- Provide clear visualizations
- Generate evidence-based recommendations

# Slide 4: Final Deliverables

## Dashboard
- Executive Summary
- Activity Scorecard
- Opportunity Matrix
- Attendance Analysis
- Monthly Recommendations
- Geography Analysis
- Volunteer Analysis

## Supporting Analysis
- Written recommendations
- Key findings summary
- Dashboard documentation
- Data refresh instructions

# Slide 5: Proposed Solution

Build a Streamlit-based decision-support dashboard combining activity, participant, and volunteer data to generate planning recommendations.

# Slide 6: Methodology

1. Data Understanding
2. Data Preparation
3. Exploratory Analysis
4. Dashboard Development
5. Validation
6. Final Delivery

# Slide 7: Data Sources

## Activity-Level Dataset
- Activity Type
- Activity Subtype
- Activity Name
- Attendance
- Volunteer Hours
- Staff Hours

## Public Signup Dataset
- City
- State
- ZIP Code
- Booking Information

## Volunteer Signup Dataset
- Certifications
- Slots Offered
- Volunteer Signups

# Slide 8: Data Progress

- Imported datasets into Python
- Created Year, Month, Day-of-Week fields
- Standardized attendance metrics
- Normalized state names
- Built Streamlit prototype
- Added filtering functionality
- Configured deployment

# Slide 9: Initial EDA

- Activity Performance
- Seasonality
- Attendance Reliability
- Geography
- Volunteer Support

# Slide 10: Dashboard Prototype

- Executive Summary
- Activity Scorecard
- Opportunity Matrix
- Yearly Trends
- Monthly Recommendations
- Attendance & No-Shows
- Geography
- Volunteer Analysis

# Slide 11: Recommendation Framework

Supply = number of activities offered

Demand = average attendance per activity

Growth Opportunity = high attendance + low activity volume

Potential Oversaturation = high activity volume + lower attendance

# Slide 12: Early Findings

- Activity and signup datasets operate at different levels
- Activity subtype is more useful than activity name
- Geography data provides outreach opportunities
- Attendance alone should not define success

# Slide 13: Risks and Open Questions

## Risks
- Historical data completeness
- Inconsistent activity naming
- Business definition validation
- Data quality issues

## Questions
- How should activity success be defined?
- Which KPIs matter most?
- What geographic level is most useful?

# Slide 14: Roadmap

## Sprint 1
- Discovery
- Data exploration
- Initial prototype

## Sprint 2
- Recommendation logic
- Improved visuals
- Validation

## Sprint 3
- Final dashboard
- Documentation
- Client handoff

# Slide 15: Team Structure

## Marcela Lozano
Project Lead / Technical Lead

## Fong
Client Liaison

## Brandon
Presentation Lead

# Slide 16: Closing

- Clear understanding of the business problem
- Working dashboard prototype
- Initial EDA completed
- Roadmap established

Thank You
