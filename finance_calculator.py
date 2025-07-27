import pandas as pd

class VehicleData:
    """
    A class to load and provide access to vehicle-specific data for TCO calculations.
    It now handles both gas and electric vehicles.
    """
    def __init__(self, filepath='vehicle_data.csv'):
        """
        Initializes the VehicleData object by loading the vehicle data from a CSV file.
        """
        try:
            self.df = pd.read_csv(filepath)
            # Create a combined 'make_model' index for easy lookup
            self.df['make_model'] = self.df['make'] + " " + self.df['model']
            self.df = self.df.set_index('make_model')
        except FileNotFoundError:
            self.df = pd.DataFrame() # Create an empty DataFrame if file is not found

    def get_vehicle_info(self, model_name):
        """
        Retrieves a dictionary of information for a specific vehicle model.
        Returns None if the model is not found.
        """
        if not self.df.empty and model_name in self.df.index:
            return self.df.loc[model_name].to_dict()
        return None

def calculate_emi(principal, annual_rate, term_years):
    """Calculates the Equated Monthly Installment (EMI) for a loan."""
    monthly_rate = (annual_rate / 100) / 12
    term_months = term_years * 12
    if monthly_rate > 0:
        emi = principal * (monthly_rate * (1 + monthly_rate)**term_months) / ((1 + monthly_rate)**term_months - 1)
    else:
        emi = principal / term_months if term_months > 0 else 0
    return emi

def calculate_total_cost_of_ownership(vehicle_info, total_loan_cost, term_years, gas_price, electricity_price):
    """
    Calculates the Total Cost of Ownership (TCO) breakdown.
    This function now dynamically calculates fuel or charging costs.
    """
    if not vehicle_info:
        return {}

    # Common costs
    insurance_cost = vehicle_info.get('avg_insurance_per_year', 0) * term_years
    maintenance_cost = vehicle_info.get('avg_maintenance_per_year', 0) * term_years

    # Dynamic fuel/charging cost calculation
    fuel_type = vehicle_info.get('fuel_type', 'Gas')
    efficiency = vehicle_info.get('efficiency', 30)
    annual_miles = 12000 # Assume average annual mileage

    total_fuel_charging_cost = 0
    if fuel_type == 'Gas':
        # Efficiency is MPG for Gas cars
        gallons_per_year = annual_miles / efficiency if efficiency > 0 else 0
        total_fuel_charging_cost = gallons_per_year * gas_price * term_years
    elif fuel_type == 'Electric':
        # Efficiency is kWh/100 miles for Electric cars
        kwh_per_year = (annual_miles / 100) * efficiency
        total_fuel_charging_cost = kwh_per_year * electricity_price * term_years

    total_tco = total_loan_cost + insurance_cost + maintenance_cost + total_fuel_charging_cost

    return {
        "Loan Payments": total_loan_cost,
        "Insurance": insurance_cost,
        "Maintenance": maintenance_cost,
        "Fuel/Charging": total_fuel_charging_cost,
        "Total TCO": total_tco
    }

def generate_amortization_and_depreciation(principal, annual_rate, term_years, emi, vehicle_price, vehicle_info):
    """
    Generates a year-by-year schedule of loan balance vs. depreciated car value.
    Note: The vehicle_info dictionary does not contain depreciation data. This will need to be added
    to the 'vehicle_data.csv' if depreciation is to be calculated. For now, it returns a static value.
    """
    schedule = []
    remaining_balance = principal
    
    # As depreciation data is missing, we'll use a placeholder static depreciation for the demo
    # A more advanced version would have this data in vehicle_data.csv
    annual_depreciation_rate = 0.15 

    for year in range(term_years + 1):
        if year == 0:
            depreciated_value = vehicle_price
        else:
            # Calculate payments made in the year
            for _ in range(12):
                interest_payment = remaining_balance * (annual_rate / 100 / 12)
                principal_payment = emi - interest_payment
                remaining_balance -= principal_payment
            
            # Placeholder depreciation logic
            depreciated_value = vehicle_price * ((1 - annual_depreciation_rate) ** year)

        schedule.append({
            "Year": year,
            "Loan_Balance": max(0, remaining_balance),
            "Car_Value": depreciated_value
        })

    return pd.DataFrame(schedule)


# Example usage block to test the functions
if __name__ == '__main__':
    # --- Test with a Gas Car (Toyota RAV4) ---
    print("--- Testing Gas Vehicle: Toyota RAV4 ---")
    vehicle_db_test = VehicleData()
    test_vehicle_info_gas = vehicle_db_test.get_vehicle_info('Toyota RAV4')
    if test_vehicle_info_gas:
        tco_gas = calculate_total_cost_of_ownership(
            vehicle_info=test_vehicle_info_gas,
            total_loan_cost=35000,
            term_years=5,
            gas_price=3.50, # $/gallon
            electricity_price=0.15 # $/kWh
        )
        print("TCO Breakdown (Gas):", tco_gas)

    # --- Test with an Electric Car (Tesla Model 3) ---
    print("\n--- Testing Electric Vehicle: Tesla Model 3 ---")
    test_vehicle_info_ev = vehicle_db_test.get_vehicle_info('Tesla Model 3')
    if test_vehicle_info_ev:
        tco_ev = calculate_total_cost_of_ownership(
            vehicle_info=test_vehicle_info_ev,
            total_loan_cost=40000,
            term_years=5,
            gas_price=3.50, # $/gallon
            electricity_price=0.15 # $/kWh
        )
        print("TCO Breakdown (EV):", tco_ev)