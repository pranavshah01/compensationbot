import pandas as pd
import random
from faker import Faker

fake = Faker()

# --- CONFIGURATION ---
NUM_MARKET_ROWS = 100
NUM_EMPLOYEES = 8000
OUTLIER_CHANCE = 0.05  # 5% Low, 5% High

# Locations with Cost of Living Multipliers
LOCATIONS = {
    'LAX': {'currency': 'USD', 'symbol': '$', 'multiplier': 1.25},
    'DUB': {'currency': 'EUR', 'symbol': '€', 'multiplier': 0.90},
    'STL': {'currency': 'USD', 'symbol': '$', 'multiplier': 0.85},
    'SHA': {'currency': 'CNY', 'symbol': '¥', 'multiplier': 3.80},
    'SYD': {'currency': 'AUD', 'symbol': '$', 'multiplier': 1.35},
    'SIN': {'currency': 'SGD', 'symbol': '$', 'multiplier': 1.45},
    'SEA': {'currency': 'USD', 'symbol': '$', 'multiplier': 1.30}
}

# Expanded Roles
ROLES = {
    # Engineering & Tech
    'Software Engineer': 115000, 'Senior Software Engineer': 165000, 'Staff Engineer': 210000,
    'Data Scientist': 125000, 'Data Analyst': 85000, 'DevOps Engineer': 130000,
    'UX Designer': 110000, 'UI Designer': 95000, 'Product Manager': 135000,
    'Project Manager': 105000, 'QA Engineer': 90000, 'System Administrator': 85000,
    'Network Engineer': 100000, 'Security Analyst': 115000, 'Cloud Architect': 160000,
    'Frontend Developer': 110000, 'Backend Developer': 115000, 'Mobile Developer': 120000,
    'Tech Lead': 180000, 'Engineering Manager': 195000, 'Director of Engineering': 230000,

    # Sales & Marketing
    'Sales Representative': 65000, 'Account Executive': 95000, 'Sales Manager': 140000,
    'Marketing Manager': 100000, 'Brand Manager': 110000, 'Content Strategist': 85000,
    'SEO Specialist': 75000, 'Social Media Manager': 70000, 'VP of Sales': 210000,
    'Customer Success Manager': 80000, 'Customer Support Lead': 65000,

    # HR, Finance & Ops
    'HR Generalist': 75000, 'Recruiter': 80000, 'HR Business Partner': 110000,
    'Office Manager': 60000, 'Executive Assistant': 80000, 'Operations Manager': 105000,
    'Business Analyst': 95000, 'Financial Analyst': 90000, 'Controller': 130000,
    'Accountant': 75000, 'Legal Counsel': 170000, 'Procurement Specialist': 85000,
    'Chief of Staff': 180000, 'Operations Coordinator': 55000
}

# --- STEP 1: GENERATE MARKET RANGES ---
market_rows = []
seen_combos = set()
print("Generating Market Ranges...")

while len(market_rows) < NUM_MARKET_ROWS:
    loc_code = random.choice(list(LOCATIONS.keys()))
    role = random.choice(list(ROLES.keys()))

    combo = f"{role}-{loc_code}"
    if combo in seen_combos: continue
    seen_combos.add(combo)

    meta = LOCATIONS[loc_code]
    base = ROLES[role] * meta['multiplier']

    # Range is Base +/- 15%
    min_sal = int(base * 0.85 / 1000) * 1000
    max_sal = int(base * 1.15 / 1000) * 1000

    market_rows.append({
        'Job Title': role,
        'Location': loc_code,
        'Currency': meta['currency'],
        'Min': min_sal,
        'Max': max_sal,
        'Compensation Range': f"{meta['symbol']}{min_sal:,} - {meta['symbol']}{max_sal:,}"
    })

df_ranges = pd.DataFrame(market_rows)

# --- STEP 2: GENERATE EMPLOYEE ROSTER ---
employee_rows = []
print("Generating Employee Roster...")

for _ in range(NUM_EMPLOYEES):
    market_role = random.choice(market_rows)
    min_market = market_role['Min']
    max_market = market_role['Max']
    band_span = max_market - min_market

    rand_check = random.random()
    salary = 0
    proficiency = ""

    # -- SCENARIO A: LOW OUTLIER (Below Min) --
    if rand_check < OUTLIER_CHANCE:
        salary = random.randint(int(min_market * 0.90), int(min_market * 0.99))
        proficiency = random.choice(['Learning', 'Learning', 'Proficient'])

    # -- SCENARIO B: HIGH OUTLIER (Above Max) --
    elif rand_check > (1 - OUTLIER_CHANCE):
        salary = random.randint(int(max_market * 1.01), int(max_market * 1.10))
        proficiency = random.choice(['Advanced', 'Advanced', 'Proficient'])

    # -- SCENARIO C: STANDARD RANGE --
    else:
        proficiency = random.choice(['Learning', 'Proficient', 'Advanced'])

        # Correlate Proficiency to Salary Band position
        if proficiency == 'Learning':
            # Bottom 40%
            sub_min = min_market
            sub_max = int(min_market + (band_span * 0.40))
        elif proficiency == 'Proficient':
            # Middle 40% (Creates overlap)
            sub_min = int(min_market + (band_span * 0.30))
            sub_max = int(min_market + (band_span * 0.70))
        else:  # Advanced
            # Top 40%
            sub_min = int(min_market + (band_span * 0.60))
            sub_max = max_market

        salary = random.randint(sub_min, sub_max)

    symbol = LOCATIONS[market_role['Location']]['symbol']

    employee_rows.append({
        'Name': fake.name(),
        'Job Title': market_role['Job Title'],
        'Proficiency': proficiency,
        'Location': market_role['Location'],
        'Compensation': f"{symbol}{salary:,}"
    })

df_employees = pd.DataFrame(employee_rows)

# --- STEP 3: EXPORT 4 FILES ---
print("Saving files...")

# Excel Versions
df_ranges.to_excel('CompRanges.xlsx', index=False)
df_employees.to_excel('EmployeeRoster.xlsx', index=False)

# CSV Versions
df_ranges.to_csv('CompRanges.csv', index=False)
df_employees.to_csv('EmployeeRoster.csv', index=False)

print("Success! Created: CompRanges.xlsx, CompRanges.csv, EmployeeRoster.xlsx, EmployeeRoster.csv")