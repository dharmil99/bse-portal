import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def generate_insights(company_name: str, sector: str, ratios: dict, scores: dict) -> str:
    prompt = f"""
You are a senior financial consultant. Analyze this company and give a concise report.

Company: {company_name}
Sector: {sector}

Financial Ratios:
- Net Margin: {ratios.get('net_margin')}%
- EBITDA Margin: {ratios.get('ebitda_margin')}%
- ROCE: {ratios.get('roce')}%
- Debt/Equity: {ratios.get('debt_to_equity')}x

Benchmark Score: {scores.get('total_score')}/100 — {scores.get('label')}

Write a 3-section report:
1. **Strengths** (2-3 bullet points)
2. **Weaknesses / Red Flags** (2-3 bullet points)
3. **Strategic Recommendations** (2-3 bullet points)

Be specific, use the numbers, keep it sharp and consulting-style.
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text