import pandas as pd

REQUIRED_COLUMNS = ["Revenue", "Ebitda", "Net Profit", "Total Debt", "Equity", "Capital Employed"]

def parse_upload(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    df.columns = [c.strip().title() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return {"error": f"Missing columns: {', '.join(missing)}"}

    row = df.iloc[0]

    try:
        data = {
            "revenue":          float(row["Revenue"]),
            "ebitda":           float(row["Ebitda"]),
            "net_profit":       float(row["Net Profit"]),
            "total_debt":       float(row["Total Debt"]),
            "equity":           float(row["Equity"]),
            "capital_employed": float(row["Capital Employed"]),
        }
    except Exception as e:
        return {"error": f"Could not parse values: {e}"}

    data["net_margin"]     = round((data["net_profit"] / data["revenue"]) * 100, 2) if data["revenue"] else 0
    data["ebitda_margin"]  = round((data["ebitda"] / data["revenue"]) * 100, 2) if data["revenue"] else 0
    data["debt_to_equity"] = round(data["total_debt"] / data["equity"], 2) if data["equity"] else 0
    data["roce"]           = round((data["ebitda"] / data["capital_employed"]) * 100, 2) if data["capital_employed"] else 0

    return data


def compute_benchmark_score(data, sector_df):
    def percentile_rank(value, series):
        return round((series < value).sum() / len(series) * 100, 1)

    scores = {}

    if "net_margin" in sector_df.columns:
        scores["margin_score"] = percentile_rank(data["net_margin"], sector_df["net_margin"])
    if "roce" in sector_df.columns:
        scores["roce_score"] = percentile_rank(data["roce"], sector_df["roce"])
    if "debt_to_equity" in sector_df.columns:
        scores["debt_score"] = 100 - percentile_rank(data["debt_to_equity"], sector_df["debt_to_equity"])
    if "ebitda_margin" in sector_df.columns:
        scores["ebitda_score"] = percentile_rank(data["ebitda_margin"], sector_df["ebitda_margin"])

    filled = [v for v in scores.values()]
    scores["total_score"] = round(sum(filled) / len(filled), 1) if filled else 0

    if scores["total_score"] >= 80:   scores["label"] = "🥇 Industry Leader"
    elif scores["total_score"] >= 60: scores["label"] = "🟢 Above Average"
    elif scores["total_score"] >= 40: scores["label"] = "🟡 Average"
    elif scores["total_score"] >= 20: scores["label"] = "🟠 Below Average"
    else:                             scores["label"] = "🔴 Needs Attention"

    return scores