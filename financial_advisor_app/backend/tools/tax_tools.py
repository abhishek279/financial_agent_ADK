# backend/tools/tax_tools.py
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# --- Simplified Tax Calculation Logic (Replace with specific jurisdiction rules) ---
# Example for Canada - VERY Simplified
# Tax brackets and rates should be fetched or configured accurately
# This example uses arbitrary progressive brackets for demonstration
TAX_BRACKETS = [
    {"limit": 50000, "rate": 0.15},
    {"limit": 100000, "rate": 0.20},
    {"limit": 150000, "rate": 0.26},
    {"limit": float('inf'), "rate": 0.33},
]
# Basic personal amount (example)
BPA = 15000 # Simplified non-refundable tax credit base

def _calculate_simplified_tax(income):
    """Calculates simplified progressive tax."""
    taxable_income = max(0, income - BPA) # Apply basic personal amount deduction concept
    tax_owing = 0
    lower_bound = 0
    for bracket in TAX_BRACKETS:
        upper_bound = bracket["limit"]
        rate = bracket["rate"]
        taxable_in_bracket = max(0, min(taxable_income, upper_bound) - lower_bound)
        tax_owing += taxable_in_bracket * rate
        if taxable_income <= upper_bound:
            break
        lower_bound = upper_bound
    return tax_owing

def calculate_tax_scenario(
    income: float,
    rrsp_contribution: float = 0.0
) -> dict:
    """
    Calculates estimated taxes before and after an RRSP contribution and the potential tax savings (refund).
    Uses simplified progressive tax brackets.

    Args:
        income (float): The user's annual gross income.
        rrsp_contribution (float): The proposed RRSP contribution amount.

    Returns:
        dict: A dictionary containing the status, estimated tax before RRSP,
              estimated tax after RRSP, and estimated tax savings (refund).
              Includes an error message on failure.
    """
    try:
        if income < 0 or rrsp_contribution < 0:
             return {"status": "error", "error_message": "Income and RRSP contribution cannot be negative."}

        # RRSP contribution reduces taxable income
        taxable_income_before = income
        taxable_income_after = max(0, income - rrsp_contribution) # Cannot go below zero

        tax_before = _calculate_simplified_tax(taxable_income_before)
        tax_after = _calculate_simplified_tax(taxable_income_after)

        tax_savings = max(0, tax_before - tax_after) # Ensure savings are not negative

        logger.info(f"Calculated tax scenario for income ${income:,.2f}, RRSP contrib ${rrsp_contribution:,.2f}. Savings: ${tax_savings:,.2f}")

        return {
            "status": "success",
            "income": income,
            "rrsp_contribution": rrsp_contribution,
            "estimated_tax_before_rrsp": round(tax_before, 2),
            "estimated_tax_after_rrsp": round(tax_after, 2),
            "estimated_tax_savings": round(tax_savings, 2)
        }
    except Exception as e:
        logger.error(f"Error in calculate_tax_scenario: {e}", exc_info=True)
        return {"status": "error", "error_message": f"An internal error occurred during tax calculation: {e}"}


def recommend_contribution_strategy(
    income: float,
    debts: List[dict], # List of dicts e.g. [{"type": "Credit Card", "balance": 3000, "interest_rate": 18}, {"type": "Mortgage", ...}]
    rrsp_room: float,
    available_funds: float = 0.0, # Optional: Funds user explicitly has available for investing/debt repayment
    tfsa_room: float = 0.0 # Added TFSA for completeness, though focus is RRSP refund
) -> dict:
    """
    Recommends an RRSP/TFSA contribution strategy considering income, high-interest debts,
    contribution room, and available funds. Prioritizes high-interest debt repayment.

    Args:
        income (float): Annual gross income.
        debts (list): A list of dictionaries, each representing a debt with 'type', 'balance', and 'interest_rate'.
        rrsp_room (float): Available RRSP contribution room.
        available_funds (float): Optional amount user has specifically set aside.
        tfsa_room (float): Available TFSA contribution room.

    Returns:
        dict: A dictionary containing the status and a recommended strategy string,
              including suggested debt payments and contributions.
              Includes an error message on failure.
    """
    try:
        if income < 0 or rrsp_room < 0 or tfsa_room < 0 or available_funds < 0:
             return {"status": "error", "error_message": "Financial figures cannot be negative."}
        if not isinstance(debts, list):
            return {"status": "error", "error_message": "Debts must be provided as a list."}

        recommendations = []
        remaining_funds = available_funds # Start with explicitly available funds

        # 1. Prioritize High-Interest Debt (e.g., > 10-12%)
        # Sort debts by interest rate, descending
        high_interest_threshold = 10.0
        sorted_debts = sorted(
            [d for d in debts if d.get('interest_rate', 0) > high_interest_threshold],
            key=lambda x: x.get('interest_rate', 0),
            reverse=True
        )

        for debt in sorted_debts:
            balance = debt.get('balance', 0)
            rate = debt.get('interest_rate', 0)
            debt_type = debt.get('type', 'Unknown Debt')

            payment_amount = 0
            if remaining_funds > 0:
                 # Pay as much as possible from available funds, up to the balance
                payment_amount = min(remaining_funds, balance)
                recommendations.append(
                    f"Prioritize paying ${payment_amount:,.2f} towards your {debt_type} "
                    f"(Balance: ${balance:,.2f} @ {rate}%) using available funds."
                )
                remaining_funds -= payment_amount
            elif balance > 0:
                 # If no explicit funds, still strongly recommend paying it down
                 recommendations.append(
                     f"Strongly recommend focusing on paying down your high-interest {debt_type} "
                     f"(Balance: ${balance:,.2f} @ {rate}%) as aggressively as possible before making significant RRSP contributions."
                 )

        # 2. Consider RRSP Contribution (if room and potentially beneficial)
        # Recommendation depends on whether high-interest debt was handled.
        suggested_rrsp = 0
        if rrsp_room > 0:
            high_interest_debt_remaining = any(
                d.get('balance', 0) > 0 and d.get('interest_rate', 0) > high_interest_threshold
                for d in debts
            )

            if not high_interest_debt_remaining:
                # High-interest debt clear, consider RRSP up to room/remaining funds
                contribute_rrsp = min(rrsp_room, remaining_funds)
                if contribute_rrsp > 0:
                     suggested_rrsp = contribute_rrsp
                     recommendations.append(
                         f"Contribute ${contribute_rrsp:,.2f} to your RRSP "
                         f"(Remaining Room: ${rrsp_room - contribute_rrsp:,.2f}). This will reduce your taxable income."
                     )
                     remaining_funds -= contribute_rrsp
                elif remaining_funds <= 0 and rrsp_room > 0:
                     # No explicit funds left, but RRSP room exists. Suggest moderate contribution if feasible from cash flow.
                     # Agent needs to infer feasibility or ask user. Here, we'll just note it.
                     recommendations.append(
                         f"You have ${rrsp_room:,.2f} RRSP room remaining. Consider making contributions from your regular cash flow if affordable, "
                         f"as high-interest debts are managed. We can calculate the potential tax savings."
                     )

            else:
                # High-interest debt exists. Recommend minimal/no RRSP unless income is very high or refund significantly helps debt.
                # This logic could be more nuanced (e.g., comparing debt rate vs marginal tax rate).
                # For simplicity, we prioritize debt heavily.
                recommendations.append(
                    f"Due to remaining high-interest debt, focus funds there first. "
                    f"Consider only minimal or no RRSP contributions (${rrsp_room:,.2f} room available) until that debt is cleared or significantly reduced. "
                    f"Let's calculate savings for a *small* contribution if you wish."
                )
                # Optionally suggest a small, symbolic contribution if user insists or has some funds left
                if remaining_funds > 0 and rrsp_room > 0:
                    small_rrsp = min(remaining_funds, rrsp_room, 1000) # Example: Cap small contribution suggestion
                    suggested_rrsp = small_rrsp
                    recommendations.append(
                        f"If you still wish to contribute to RRSP now, consider a smaller amount like ${small_rrsp:,.2f} "
                        f"(using remaining available funds) to keep momentum while prioritizing debt."
                    )
                    remaining_funds -= small_rrsp


        # 3. Consider TFSA (if room and funds remain) - Lower priority than RRSP for tax refund focus
        if tfsa_room > 0 and remaining_funds > 0:
             contribute_tfsa = min(tfsa_room, remaining_funds)
             recommendations.append(
                 f"Contribute ${contribute_tfsa:,.2f} to your TFSA "
                 f"(Remaining Room: ${tfsa_room - contribute_tfsa:,.2f}) for tax-free growth."
             )
             remaining_funds -= contribute_tfsa

        if not recommendations:
            recommendations.append("Based on the provided information, no specific actions recommended regarding contributions or high-interest debt at this time. Ensure all debts are being managed.")

        logger.info(f"Generated contribution strategy. Recommendations: {recommendations}")

        return {
            "status": "success",
            "suggested_rrsp_contribution": round(suggested_rrsp, 2), # Return suggested amount for potential follow-up
            "recommendation_details": "\n".join(f"- {rec}" for rec in recommendations)
        }

    except Exception as e:
        logger.error(f"Error in recommend_contribution_strategy: {e}", exc_info=True)
        return {"status": "error", "error_message": f"An internal error occurred during strategy recommendation: {e}"}