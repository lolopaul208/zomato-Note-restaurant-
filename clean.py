"""
Zomato Restaurant Dataset — cleaning script
Input : data/raw.csv  (Kaggle "Zomato Restaurant Dataset", 9,551 rows x 21 cols)
Output: data/restaurants_clean.csv   one row per restaurant (all countries)
        data/restaurant_cuisines.csv one row per restaurant x cuisine (for Power BI / Tableau)

Usage: python clean.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw.csv"
OUT = HERE / "data"

COUNTRIES = {  # Zomato country codes present in this dataset
    1: "India", 14: "Australia", 30: "Brazil", 37: "Canada", 94: "Indonesia",
    148: "New Zealand", 162: "Philippines", 166: "Qatar", 184: "Singapore",
    189: "South Africa", 191: "Sri Lanka", 208: "Turkey", 214: "UAE",
    215: "United Kingdom", 216: "United States",
}
NCR = {"New Delhi", "Gurgaon", "Noida", "Faridabad", "Ghaziabad"}

df = pd.read_csv(RAW, encoding_errors="replace")
n0 = len(df)

# 1. Column names -> snake_case
df.columns = (df.columns.str.strip().str.lower()
              .str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_"))

# 2. Drop columns with no information
#    switch_to_order_menu = "No" for every row; is_delivering_now = "Yes" for 34 rows only;
#    locality_verbose duplicates locality + city; rating_color duplicates rating_text.
df = df.drop(columns=["switch_to_order_menu", "is_delivering_now",
                      "locality_verbose", "rating_color"])

# 3. Country names, clean currency label (raw file has an encoding error on £)
df["country"] = df["country_code"].map(COUNTRIES)
df["currency"] = df["currency"].str.replace(r"Pounds\(.*\)", "Pounds(GBP)", regex=True)
df["region"] = np.where(df["city"].isin(NCR), "Delhi NCR",
                        np.where(df["country"] == "India", "India - other cities", df["country"]))

# 4. Yes/No -> boolean
for c in ["has_table_booking", "has_online_delivery"]:
    df[c] = df[c].eq("Yes")

# 5. Ratings: 0.0 means "Not rated" (fewer than 4 votes), NOT a score of zero
df["is_rated"] = df["aggregate_rating"] > 0
df.loc[~df["is_rated"], "aggregate_rating"] = np.nan

# 6. Cost: 0 = missing. Costs are in local currency -> only comparable within a country.
df.loc[df["average_cost_for_two"] == 0, "average_cost_for_two"] = np.nan

# 7. Coordinates: (0, 0) = missing
missing_geo = (df["latitude"] == 0) & (df["longitude"] == 0)
df.loc[missing_geo, ["latitude", "longitude"]] = np.nan

# 8. Cuisines: trim, count, primary cuisine
df["cuisines"] = df["cuisines"].fillna("Unknown").str.strip()
cuisine_lists = df["cuisines"].str.split(",").apply(lambda l: [x.strip() for x in l if x.strip()])
df["n_cuisines"] = cuisine_lists.str.len()
df["primary_cuisine"] = cuisine_lists.str[0]

# 9. Chain flag: same name appears 5+ times in the dataset
counts = df["restaurant_name"].str.strip().str.lower().map(
    df["restaurant_name"].str.strip().str.lower().value_counts())
df["is_chain"] = counts >= 5

# 10. Price range labels
df["price_label"] = df["price_range"].map({1: "1 - Budget", 2: "2 - Mid-range",
                                          3: "3 - Upscale", 4: "4 - Fine dining"})

df.to_csv(OUT / "restaurants_clean.csv", index=False)

long = (df[["restaurant_id"]].assign(cuisine=cuisine_lists).explode("cuisine"))
long.to_csv(OUT / "restaurant_cuisines.csv", index=False)

print(f"rows in/out: {n0} / {len(df)}")
print(f"not rated -> NaN: {(~df['is_rated']).sum()}")
print(f"missing coordinates -> NaN: {missing_geo.sum()}")
print(f"cost 0 -> NaN: {df['average_cost_for_two'].isna().sum()}")
print(f"restaurant x cuisine rows: {len(long)}")
