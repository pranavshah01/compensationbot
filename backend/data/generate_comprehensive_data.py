import pandas as pd
import random
from faker import Faker

fake = Faker()

# --- CONFIGURATION ---
NUM_EMPLOYEES_PER_ROLE_LOCATION = 10  # Number of employees per role-location combination
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

# Job Families
JOB_FAMILIES = {
    'Engineering': {
        'Software Engineer': 115000,
        'Senior Software Engineer': 165000,
        'Staff Engineer': 210000,
        'Data Scientist': 125000,
        'Data Analyst': 85000,
        'DevOps Engineer': 130000,
        'UX Designer': 110000,
        'UI Designer': 95000,
        'Product Manager': 135000,
        'QA Engineer': 90000,
        'System Administrator': 85000,
        'Network Engineer': 100000,
        'Security Analyst': 115000,
        'Cloud Architect': 160000,
        'Frontend Developer': 110000,
        'Backend Developer': 115000,
        'Mobile Developer': 120000,
        'Tech Lead': 180000,
        'Engineering Manager': 195000,
        'Director of Engineering': 230000
    },
    'Sales': {
        'Sales Representative': 65000,
        'Account Executive': 95000,
        'Sales Manager': 140000,
        'VP of Sales': 210000,
        'Customer Success Manager': 80000,
        'Customer Support Lead': 65000
    },
    'Marketing': {
        'Marketing Manager': 100000,
        'Brand Manager': 110000,
        'Content Strategist': 85000,
        'SEO Specialist': 75000,
        'Social Media Manager': 70000
    },
    'HR': {
        'HR Generalist': 75000,
        'Recruiter': 80000,
        'HR Business Partner': 110000
    },
    'Finance': {
        'Business Analyst': 95000,
        'Financial Analyst': 90000,
        'Controller': 130000,
        'Accountant': 75000
    },
    'Operations': {
        'Office Manager': 60000,
        'Executive Assistant': 80000,
        'Operations Manager': 105000,
        'Operations Coordinator': 55000,
        'Procurement Specialist': 85000
    },
    'Legal': {
        'Legal Counsel': 170000
    },
    'Executive': {
        'Chief of Staff': 180000,
        'Project Manager': 105000
    }
}

# Flatten all roles for easy access
ALL_ROLES = {}
for job_family, roles in JOB_FAMILIES.items():
    for role, base_salary in roles.items():
        ALL_ROLES[role] = {'base_salary': base_salary, 'job_family': job_family}

# --- STEP 1: GENERATE MARKET RANGES FOR ALL COMBINATIONS ---
print("Generating Market Ranges for ALL combinations...")
market_rows = []

# Generate market ranges for ALL role-location combinations
for role, role_info in ALL_ROLES.items():
    for loc_code, loc_meta in LOCATIONS.items():
        base = role_info['base_salary'] * loc_meta['multiplier']
        
        # Range is Base +/- 15%
        min_sal = int(base * 0.85 / 1000) * 1000
        max_sal = int(base * 1.15 / 1000) * 1000
        
        market_rows.append({
            'Job Title': role,
            'Location': loc_code,
            'Currency': loc_meta['currency'],
            'Min': min_sal,
            'Max': max_sal,
            'Compensation Range': f"{loc_meta['symbol']}{min_sal:,} - {loc_meta['symbol']}{max_sal:,}"
        })

df_ranges = pd.DataFrame(market_rows)
print(f"Generated {len(market_rows)} market range entries")

# --- STEP 2: GENERATE EMPLOYEE ROSTER WITH JOB FAMILY ---
print("Generating Employee Roster with Job Family...")
employee_rows = []

# Generate employees for each role-location combination
for role, role_info in ALL_ROLES.items():
    job_family = role_info['job_family']
    
    # Find market ranges for this role
    role_market_ranges = df_ranges[df_ranges['Job Title'] == role]
    
    for _, market_range in role_market_ranges.iterrows():
        location = market_range['Location']
        min_market = market_range['Min']
        max_market = market_range['Max']
        band_span = max_market - min_market
        symbol = LOCATIONS[location]['symbol']
        
        # Generate NUM_EMPLOYEES_PER_ROLE_LOCATION employees for this role-location combo
        for _ in range(NUM_EMPLOYEES_PER_ROLE_LOCATION):
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

            employee_rows.append({
                'Name': fake.name(),
                'Job Title': role,
                'Job Family': job_family,
                'Proficiency': proficiency,
                'Location': location,
                'Compensation': f"{symbol}{salary:,}"
            })

df_employees = pd.DataFrame(employee_rows)
print(f"Generated {len(employee_rows)} employee entries")

# --- STEP 3: EXPORT FILES ---
print("\nSaving files...")

# Excel Versions
df_ranges.to_excel('CompRanges.xlsx', index=False)
df_employees.to_excel('EmployeeRoster.xlsx', index=False)

# CSV Versions
df_ranges.to_csv('CompRanges.csv', index=False)
df_employees.to_csv('EmployeeRoster.csv', index=False)

# Summary Statistics
print("\n=== SUMMARY ===")
print(f"Total Market Range Entries: {len(df_ranges)}")
print(f"  - Unique Job Titles: {df_ranges['Job Title'].nunique()}")
print(f"  - Unique Locations: {df_ranges['Location'].nunique()}")
print(f"  - Unique Combinations: {len(df_ranges)}")
print(f"\nTotal Employee Entries: {len(df_employees)}")
print(f"  - Unique Job Titles: {df_employees['Job Title'].nunique()}")
print(f"  - Unique Job Families: {df_employees['Job Family'].nunique()}")
print(f"  - Unique Locations: {df_employees['Location'].nunique()}")
print(f"\nJob Family Distribution:")
for job_family in sorted(df_employees['Job Family'].unique()):
    count = len(df_employees[df_employees['Job Family'] == job_family])
    print(f"  - {job_family}: {count} employees")

print("\n✅ Success! Created:")
print("  - CompRanges.xlsx")
print("  - CompRanges.csv")
print("  - EmployeeRoster.xlsx")
print("  - EmployeeRoster.csv")
print("\nNote: EmployeeRoster now includes 'Job Family' column!")

