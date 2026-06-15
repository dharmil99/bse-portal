import pandas as pd

file_path = r"C:\Users\Jignesh\Desktop\bse_portal\data\raw\Infosys.xlsx"

# Load raw
df = pd.read_excel(file_path, header=None)

# Row 2 is the real header (Narration + years)
# Set row 2 as column names
df.columns = df.iloc[2]

# Set first column as index (Sales, Expenses etc)
df = df.set_index(df.columns[0])

# Drop rows 0,1,2 — they were headers
df = df.iloc[3:]

# Drop columns that are not years (NaN columns, Trailing, Best Case etc)
df = df.loc[:, df.columns.notna()]
df.columns = df.columns.astype(str)
df = df[[col for col in df.columns if col.startswith('201') or col.startswith('202')]]

# Shorten column names to just the year
df.columns = [col[:4] for col in df.columns]

# Convert to numbers
df = df.apply(pd.to_numeric, errors='coerce')

print("✅ Clean data ready!")
print("Years:", df.columns.tolist())
print("\nRow names:", df.index.tolist())

# Extract metrics
sales      = df.loc['Sales']
op_profit  = df.loc['Operating Profit']
net_profit = df.loc['Net profit']
eps        = df.loc['EPS']

# Calculate margins
op_margin  = (op_profit / sales * 100).round(1)
net_margin = (net_profit / sales * 100).round(1)

# Display clean table
print("\n📊 INFOSYS FINANCIALS (₹ Crores)")
print("=" * 60)
print(f"\n{'Metric':<18}", "  ".join(df.columns.tolist()))
print("-" * 60)

for label, data in [
    ('Sales', sales),
    ('Operating Profit', op_profit),
    ('Net Profit', net_profit),
    ('EPS (₹)', eps),
    ('OPM %', op_margin),
    ('Net Margin %', net_margin),
]:
    vals = "  ".join(f"{v:>8.0f}" for v in data)
    print(f"{label:<18} {vals}")

# Save
out = r"C:\Users\Jignesh\Desktop\bse_portal\data\clean\infosys_clean.csv"
df.to_csv(out)
print(f"\n✅ Saved clean file to data/clean/infosys_clean.csv")