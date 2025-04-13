# backend/tools/mortgage_tools.py
import logging
import numpy_financial as npf # For mortgage calculations

logger = logging.getLogger(__name__)

def _calculate_monthly_payment(principal, annual_interest_rate, years):
    """Calculates the fixed monthly mortgage payment."""
    if principal <= 0 or annual_interest_rate < 0 or years <= 0:
        return 0
    monthly_rate = (annual_interest_rate / 100) / 12
    num_payments = years * 12
    # Use numpy_financial.pmt - Note: it returns a negative value for payment
    payment = -npf.pmt(monthly_rate, num_payments, principal)
    return payment

def analyze_mortgage_profile(
    principal: float,
    annual_interest_rate: float,
    remaining_amortization_years: float
) -> dict:
    """
    Analyzes the current mortgage profile to determine monthly payment and estimated total interest.

    Args:
        principal (float): The current outstanding mortgage principal.
        annual_interest_rate (float): The annual interest rate (e.g., 5 for 5%).
        remaining_amortization_years (float): The number of years left in the amortization period.

    Returns:
        dict: A dictionary containing the status, calculated monthly payment,
              and estimated total interest remaining. Includes an error message on failure.
    """
    try:
        if principal <= 0 or annual_interest_rate < 0 or remaining_amortization_years <= 0:
            return {"status": "error", "error_message": "Invalid mortgage parameters provided."}

        monthly_payment = _calculate_monthly_payment(principal, annual_interest_rate, remaining_amortization_years)
        if monthly_payment == 0:
             return {"status": "error", "error_message": "Could not calculate monthly payment with provided inputs."}

        total_paid = monthly_payment * remaining_amortization_years * 12
        total_interest = total_paid - principal

        logger.info(f"Analyzed mortgage: P=${principal:,.2f}, Rate={annual_interest_rate}%, Years={remaining_amortization_years}. Payment=${monthly_payment:,.2f}, Interest=${total_interest:,.2f}")

        return {
            "status": "success",
            "current_principal": principal,
            "annual_interest_rate": annual_interest_rate,
            "remaining_amortization_years": remaining_amortization_years,
            "estimated_monthly_payment": round(monthly_payment, 2),
            "estimated_total_interest_remaining": round(total_interest, 2)
        }
    except Exception as e:
        logger.error(f"Error in analyze_mortgage_profile: {e}", exc_info=True)
        return {"status": "error", "error_message": f"An internal error occurred during mortgage analysis: {e}"}


def generate_acceleration_scenario(
    principal: float,
    annual_interest_rate: float,
    remaining_amortization_years: float,
    extra_monthly_payment: float = 0.0,
    lump_sum_payment: float = 0.0
) -> dict:
    """
    Calculates the impact of making extra monthly payments or a lump-sum payment on the mortgage payoff time and total interest paid.

    Args:
        principal (float): Current outstanding mortgage principal.
        annual_interest_rate (float): Annual interest rate (e.g., 5 for 5%).
        remaining_amortization_years (float): Years left in the original amortization.
        extra_monthly_payment (float): Additional amount paid each month.
        lump_sum_payment (float): A one-time extra payment applied immediately.

    Returns:
        dict: A dictionary containing the status, original payoff details, new payoff details (time, interest),
              time saved, and interest saved. Includes an error message on failure.
    """
    try:
        if principal <= 0 or annual_interest_rate < 0 or remaining_amortization_years <= 0 or extra_monthly_payment < 0 or lump_sum_payment < 0:
            return {"status": "error", "error_message": "Invalid mortgage or payment parameters provided."}

        # --- Baseline Calculation ---
        original_monthly_payment = _calculate_monthly_payment(principal, annual_interest_rate, remaining_amortization_years)
        original_total_interest = (original_monthly_payment * remaining_amortization_years * 12) - principal

        # --- Accelerated Calculation ---
        current_principal = principal - lump_sum_payment # Apply lump sum first
        if current_principal <= 0:
             return {
                 "status": "success",
                 "scenario_description": f"Applying a lump sum of ${lump_sum_payment:,.2f} pays off the remaining principal of ${principal:,.2f} immediately!",
                 "original_payoff_years": round(remaining_amortization_years, 2),
                 "original_total_interest": round(original_total_interest, 2),
                 "new_payoff_years": 0,
                 "new_total_interest": 0,
                 "years_saved": round(remaining_amortization_years, 2),
                 "interest_saved": round(original_total_interest + lump_sum_payment - principal, 2) # Interest saved + part of lump sum that covered principal
             }

        new_monthly_payment = original_monthly_payment + extra_monthly_payment
        monthly_rate = (annual_interest_rate / 100) / 12

        if monthly_rate == 0: # Handle zero interest rate case
            if new_monthly_payment <=0:
                 return {"status": "error", "error_message": "Cannot calculate payoff time with zero interest and zero/negative payment."}
            new_num_payments = current_principal / new_monthly_payment # Months to pay off
        else:
            # Use numpy_financial.nper to find the number of periods (months)
            # Ensure payment is negative for the formula
            new_num_payments = npf.nper(monthly_rate, -new_monthly_payment, current_principal)

        new_payoff_years = new_num_payments / 12
        new_total_paid = (new_monthly_payment * new_num_payments) + lump_sum_payment # Total cash outflow
        new_total_interest = new_total_paid - principal # Total interest paid across the accelerated period

        years_saved = remaining_amortization_years - new_payoff_years
        interest_saved = original_total_interest - new_total_interest

        scenario_desc = f"Applying a lump sum of ${lump_sum_payment:,.2f} and an extra ${extra_monthly_payment:,.2f}/month:"

        logger.info(f"Generated acceleration scenario: {scenario_desc}. Years Saved={years_saved:.2f}, Interest Saved=${interest_saved:,.2f}")

        return {
            "status": "success",
            "scenario_description": scenario_desc,
            "original_payoff_years": round(remaining_amortization_years, 2),
            "original_total_interest": round(original_total_interest, 2),
            "new_payoff_years": round(new_payoff_years, 2),
            "new_total_interest": round(new_total_interest, 2),
            "years_saved": round(years_saved, 2),
            "interest_saved": round(interest_saved, 2)
        }

    except ValueError as ve:
         # Catch cases where nper might return NaN or inf if payment doesn't cover interest
         logger.error(f"Error calculating NPER in acceleration scenario: {ve}", exc_info=True)
         if "Cannot calculate number of periods" in str(ve) or "net payment is too small" in str(ve).lower():
              return {"status": "error", "error_message": f"Calculation error: The payment amount (${new_monthly_payment:,.2f}/month) may not be sufficient to cover the interest on the principal (${current_principal:,.2f})."}
         else:
             return {"status": "error", "error_message": f"A calculation error occurred: {ve}"}
    except Exception as e:
        logger.error(f"Error in generate_acceleration_scenario: {e}", exc_info=True)
        return {"status": "error", "error_message": f"An internal error occurred during acceleration scenario generation: {e}"}