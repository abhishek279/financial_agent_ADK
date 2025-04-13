# backend/agents/financial_advisor_agent.py
import logging
from google.adk.agents import Agent
# Import the tool functions directly
from tools.tax_tools import calculate_tax_scenario, recommend_contribution_strategy
from tools.mortgage_tools import analyze_mortgage_profile, generate_acceleration_scenario

logging.basicConfig(level=logging.INFO) # Basic logging setup for ADK/tools

# Combine all tools into one list for the agent
all_tools = [
    calculate_tax_scenario,
    recommend_contribution_strategy,
    analyze_mortgage_profile,
    generate_acceleration_scenario
]

# Define the root agent
root_agent = Agent(
    name="financial_advisor",
    model="gemini-1.5-flash-001", # Or another suitable Gemini model
    description=(
        "A comprehensive financial advisor agent that provides personalized advice "
        "on tax planning (RRSP/TFSA contributions) and mortgage acceleration. "
        "It prioritizes high-interest debt repayment and aims to optimize overall financial health."
    ),
    instruction=(
        "You are an intelligent financial advisor. Your goal is to help users reduce taxes "
        "and pay off their mortgage faster, while carefully considering their overall financial situation, "
        "especially existing debts. \n\n"
        "**Input:** You will receive user financial data, potentially structured from a form. Key fields include: "
        "income, debts (list with type, balance, rate), RRSP/TFSA room, mortgage details (principal, rate, years), "
        "available funds, and potential extra mortgage payments (monthly/lump sum).\n\n"
        "**Workflow:**\n"
        "1.  **Analyze Input:** Parse the provided financial data.\n"
        "2.  **Assess Debt:** Use `recommend_contribution_strategy` with the provided income and debts "
        "    to identify high-interest debts and recommend prioritization.\n"
        "3.  **Recommend Contributions:** Based on the debt assessment, RRSP/TFSA room, and available funds, "
        "    use `recommend_contribution_strategy` again (or use its output from step 2) to suggest optimal contribution amounts. "
        "    Explain the rationale clearly.\n"
        "4.  **Calculate Tax Impact:** If an RRSP contribution is suggested or makes sense based on the data, "
        "    use `calculate_tax_scenario` with the income and the suggested RRSP contribution to estimate tax savings/refund.\n"
        "5.  **Mortgage Analysis:** If mortgage details (principal, rate, years) are provided and valid, "
        "    use `analyze_mortgage_profile` to show the current situation.\n"
        "6.  **Mortgage Acceleration:** If a potential tax refund is calculated (from step 4), or if `lump_sum_payment` or `extra_monthly_payment` "
        "    values are provided (and affordable after considering high-interest debt), use `generate_acceleration_scenario` "
        "    with the mortgage details and these extra payment amounts. Clearly link the source of funds (e.g., tax refund, specified lump sum).\n"
        "7.  **Synthesize Advice:** Combine the findings from the tools into a comprehensive, actionable summary. "
        "    Explain the interconnected benefits. Prioritize financial stability.\n"
        "8.  **Be Clear and Explanatory:** Use the results from the tools for concrete numbers and provide clear explanations."

    ),
    tools=all_tools
    # REMOVED: enable_memory=True,  <- This line was causing the error
)