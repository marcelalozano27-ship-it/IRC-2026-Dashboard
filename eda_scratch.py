import csv, collections, statistics

with open('C:/Users/fongl/OneDrive/Documents/Capstone/IRC-2026/data/LGO Participation 2025.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Deduplicate to event level
seen = set()
acts = []
for r in rows:
    if r['ActivityID'] not in seen:
        seen.add(r['ActivityID'])
        acts.append(r)

print('=== DATA STRUCTURE ===')
print(f'Total booking rows: {len(rows)}')
print(f'Unique events: {len(acts)}')
print(f'Unique participants: {len(set(r["user_id"] for r in rows))}')
print(f'Date range: {min(r["Date"] for r in acts)} to {max(r["Date"] for r in acts)}')

print('\n=== MISSING / BLANK VALUES (event level) ===')
for col in rows[0].keys():
    blank = sum(1 for r in acts if not r[col].strip())
    if blank > 0:
        print(f'  {col}: {blank} blank ({blank/len(acts)*100:.1f}%)')

print('\n=== ACTIVITY TYPE BREAKDOWN ===')
at = collections.Counter(r['ActivityType'] for r in acts)
for k,v in sorted(at.items(), key=lambda x:-x[1]):
    print(f'  {k or "(blank)"}: {v} events ({v/len(acts)*100:.1f}%)')

print('\n=== ORGANIZATION BREAKDOWN (events) ===')
org_events = collections.Counter(r['Organization'] for r in acts)
for k,v in org_events.most_common(10):
    print(f'  {k}: {v} events')

print('\n=== IRC-LED vs NOT ===')
irc = collections.Counter(r['IsIrcLed'] for r in acts)
print(f'  IRC-Led (1): {irc["1"]} events ({irc["1"]/len(acts)*100:.1f}%)')
print(f'  Not IRC-Led (0): {irc["0"]} events ({irc["0"]/len(acts)*100:.1f}%)')

print('\n=== CAPACITY & ATTENDANCE ===')
spaces = [int(r['total_spaces']) for r in acts if r['total_spaces'] and r['total_spaces'] != '0']
registered = [int(r['VisitorsRegistered']) for r in acts if r['VisitorsRegistered']]
total_v = [int(r['TotalVisitors']) for r in acts if r['TotalVisitors']]
noshows = [int(r['VisitorsNoShow']) for r in acts if r['VisitorsNoShow']]
walkups = [int(r['VisitorsWalkUp']) for r in acts if r['VisitorsWalkUp']]

util = []
for r in acts:
    sp = int(r['total_spaces']) if r['total_spaces'] else 0
    tv = int(r['TotalVisitors']) if r['TotalVisitors'] else 0
    if sp > 0:
        util.append(tv / sp)

print(f'  Avg capacity (spaces): {statistics.mean(spaces):.1f}')
print(f'  Avg TotalVisitors: {statistics.mean(total_v):.1f}')
print(f'  Median TotalVisitors: {statistics.median(total_v):.1f}')
print(f'  Max TotalVisitors: {max(total_v)}')
print(f'  Events with 0 visitors: {sum(1 for v in total_v if v==0)} ({sum(1 for v in total_v if v==0)/len(total_v)*100:.1f}%)')
print(f'  Avg capacity utilization: {statistics.mean(util)*100:.1f}%')
print(f'  Median capacity utilization: {statistics.median(util)*100:.1f}%')

buckets = {'<25%':0,'25-50%':0,'50-75%':0,'75-100%':0,'>100%':0}
for u in util:
    if u < 0.25: buckets['<25%'] += 1
    elif u < 0.50: buckets['25-50%'] += 1
    elif u < 0.75: buckets['50-75%'] += 1
    elif u <= 1.0: buckets['75-100%'] += 1
    else: buckets['>100%'] += 1
print(f'  Utilization distribution: {buckets}')

print('\n=== NO-SHOW ANALYSIS ===')
ns_rate_per_event = []
for r in acts:
    reg = int(r['VisitorsRegistered']) if r['VisitorsRegistered'] else 0
    ns = int(r['VisitorsNoShow']) if r['VisitorsNoShow'] else 0
    if reg > 0:
        ns_rate_per_event.append(ns/reg)

print(f'  Overall no-show rate: {sum(noshows)/sum(registered)*100:.1f}%')
print(f'  Avg no-show rate per event: {statistics.mean(ns_rate_per_event)*100:.1f}%')
print(f'  Events with 0% no-shows: {sum(1 for r in ns_rate_per_event if r==0)} ({sum(1 for r in ns_rate_per_event if r==0)/len(ns_rate_per_event)*100:.1f}%)')
print(f'  Events with >50% no-show: {sum(1 for r in ns_rate_per_event if r>0.5)} ({sum(1 for r in ns_rate_per_event if r>0.5)/len(ns_rate_per_event)*100:.1f}%)')

ns_by_type = collections.defaultdict(lambda: [0,0])
for r in acts:
    reg = int(r['VisitorsRegistered']) if r['VisitorsRegistered'] else 0
    ns = int(r['VisitorsNoShow']) if r['VisitorsNoShow'] else 0
    ns_by_type[r['ActivityType']][0] += ns
    ns_by_type[r['ActivityType']][1] += reg
print('  No-show rate by activity type:')
for k,v in sorted(ns_by_type.items(), key=lambda x: -x[1][0]/x[1][1] if x[1][1]>0 else 0):
    if v[1] > 0:
        print(f'    {k or "(blank)"}: {v[0]/v[1]*100:.1f}% ({v[0]}/{v[1]})')

print('\n=== WALK-UPS ===')
print(f'  Total walk-up visitors: {sum(walkups)}')
print(f'  Avg walk-ups per event: {statistics.mean(walkups):.1f}')
print(f'  Events with walk-ups: {sum(1 for w in walkups if w>0)} ({sum(1 for w in walkups if w>0)/len(walkups)*100:.1f}%)')

print('\n=== CANCELLATIONS ===')
cancelled = [r for r in acts if r['ActivityStatus'] == 'Cancelled']
print(f'  Total cancelled: {len(cancelled)} / {len(acts)} = {len(cancelled)/len(acts)*100:.1f}%')
cancel_by_type = collections.Counter(r['ActivityType'] for r in cancelled)
print('  Cancellations by type (rate):')
for k,v in cancel_by_type.most_common():
    total_type = at[k]
    print(f'    {k or "(blank)"}: {v}/{total_type} = {v/total_type*100:.1f}%')
cancel_codes = collections.Counter(r['CancelReason'] for r in cancelled)
print(f'  Cancellation codes: {dict(cancel_codes)}')

print('\n=== SEASONALITY (active events per month) ===')
months = collections.Counter(r['Date'][:7] for r in acts if r['ActivityStatus'] != 'Cancelled')
for m,v in sorted(months.items()):
    bar = '#' * (v // 3)
    print(f'  {m}: {v:3d} {bar}')

print('\n=== MONTHLY ATTENDANCE ===')
monthly_visitors = collections.defaultdict(int)
for r in acts:
    if r['ActivityStatus'] != 'Cancelled':
        monthly_visitors[r['Date'][:7]] += int(r['TotalVisitors']) if r['TotalVisitors'] else 0
for m,v in sorted(monthly_visitors.items()):
    print(f'  {m}: {v} visitors')

print('\n=== STAFFING ===')
vols = [int(r['Volunteers']) for r in acts if r['Volunteers']]
staff = [int(r['Staff']) for r in acts if r['Staff']]
vol_hrs = [float(r['VolunteerHours']) for r in acts if r['VolunteerHours']]
staff_hrs = [float(r['StaffHours']) for r in acts if r['StaffHours']]
print(f'  Avg volunteers per event: {statistics.mean(vols):.1f} (total: {sum(vols)})')
print(f'  Avg staff per event: {statistics.mean(staff):.1f} (total: {sum(staff)})')
print(f'  Total volunteer hours: {sum(vol_hrs):,.0f}')
print(f'  Total staff hours: {sum(staff_hrs):,.0f}')
print(f'  Events with 0 volunteers: {sum(1 for v in vols if v==0)} ({sum(1 for v in vols if v==0)/len(vols)*100:.1f}%)')

print('\n=== GEOGRAPHY ===')
cities = collections.Counter(r['city'] for r in rows if r['city'])
print('  Top 15 participant cities:')
for city, cnt in cities.most_common(15):
    print(f'    {city}: {cnt} bookings ({cnt/len(rows)*100:.1f}%)')

irvine_res = sum(int(r['VisitorsRegisteredIrvineResident']) for r in acts if r['VisitorsRegisteredIrvineResident'])
irvine_nonres = sum(int(r['VisitorsRegisteredIrvineNonResident']) for r in acts if r['VisitorsRegisteredIrvineNonResident'])
print(f'  Irvine Resident registrations: {irvine_res}')
print(f'  Irvine Non-Resident registrations: {irvine_nonres}')
if irvine_res+irvine_nonres > 0:
    print(f'  Irvine Resident share: {irvine_res/(irvine_res+irvine_nonres)*100:.1f}%')

print('\n=== PRIVATE / UNLISTED ===')
private = collections.Counter(r['IsPrivate'] for r in acts)
unlisted = collections.Counter(r['IsUnlisted'] for r in acts)
print(f'  Private events: {private["1"]} ({private["1"]/len(acts)*100:.1f}%)')
print(f'  Unlisted events: {unlisted["1"]} ({unlisted["1"]/len(acts)*100:.1f}%)')

print('\n=== CHILDREN & TOTAL GUESTS ===')
children = [int(r['VisitorsChildren']) for r in acts if r['VisitorsChildren']]
total_guests = [int(r['TotalGuests']) for r in acts if r['TotalGuests']]
print(f'  Total children across events: {sum(children)}')
print(f'  Avg children per event: {statistics.mean(children):.1f}')
print(f'  Events with children: {sum(1 for c in children if c>0)} ({sum(1 for c in children if c>0)/len(children)*100:.1f}%)')
print(f'  Total guests (visitors+children): {sum(total_guests)}')

print('\n=== REPEAT PARTICIPANTS ===')
user_events = collections.Counter(r['user_id'] for r in rows)
once = sum(1 for v in user_events.values() if v == 1)
multi = sum(1 for v in user_events.values() if v > 1)
print(f'  Attended once: {once} ({once/len(user_events)*100:.1f}%)')
print(f'  Attended 2+ times: {multi} ({multi/len(user_events)*100:.1f}%)')
print(f'  Max bookings by one user: {max(user_events.values())}')
top_users = user_events.most_common(5)
print(f'  Top 5 users (bookings): {top_users}')

print('\n=== DAY OF WEEK ===')
import datetime
dow = collections.Counter()
for r in acts:
    if r['ActivityStatus'] != 'Cancelled':
        try:
            d = datetime.date.fromisoformat(r['Date'])
            dow[d.strftime('%A')] += 1
        except: pass
days_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
for day in days_order:
    print(f'  {day}: {dow[day]}')
