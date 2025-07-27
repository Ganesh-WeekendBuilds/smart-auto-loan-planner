import streamlit as st
import pandas as pd
import joblib
import plotly.graph_objects as go
from finance_calculator import (
    VehicleData,
    calculate_emi,
    calculate_total_cost_of_ownership,
    generate_amortization_and_depreciation
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Smart Auto Loan Planner",
    page_icon="🚗",
    layout="wide"
)

# --- Custom CSS for a clean, modern UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* General Styling */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #F0F2F6; /* Light gray background */
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    
    /* Card for metrics and sections */
    .section-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 25px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        height: 100%;
    }
    
    .metric-card .title {
        font-size: 0.9rem;
        color: #4A5568;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1A202C;
        line-height: 1.2;
    }
    
    h1, h2, h3 {
        font-weight: 700 !important;
    }

    /* Affordability box styling */
    .affordability-box {
        padding: 15px;
        border-radius: 12px;
        margin-top: 10px;
        border-left: 5px solid;
    }
    .affordability-box.good { background-color: #F0FFF4; border-color: #48BB78; }
    .affordability-box.borderline { background-color: #FFFBEB; border-color: #F6E05E; }
    .affordability-box.high-risk { background-color: #FFF5F5; border-color: #F56565; }
    .affordability-box .status { font-weight: 700; font-size: 16px; margin-bottom: 5px; }
    
    /* How it works styling */
    .how-it-works h6 {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.5rem;
        margin-top: 0.5rem;
        color: #2D3748;
    }
</style>
""", unsafe_allow_html=True)


# --- Load Models and Data ---
@st.cache_resource
def load_resources():
    """Loads the ML model, model columns, and vehicle data."""
    try:
        model = joblib.load('interest_rate_model.joblib')
        model_cols = joblib.load('model_columns.joblib')
        vehicle_db = VehicleData('vehicle_data.csv')
        return model, model_cols, vehicle_db
    except FileNotFoundError:
        st.error("Error: Model or data files not found. Please run the setup scripts first.")
        return None, None, None

model, model_cols, vehicle_db = load_resources()

# --- Main App ---
if model and model_cols and vehicle_db:
    st.title("🚗 Smart Auto Loan Planner")

    # --- Sidebar for User Inputs ---
    with st.sidebar:
        st.title("Loan Configurator")
        st.header("1. Vehicle & Loan")
        # Adjusted defaults to better showcase the 'underwater' feature
        vehicle_price = st.slider("Vehicle Price ($)", 5000, 100000, 40000, 1000)
        down_payment = st.slider("Down Payment ($)", 0, vehicle_price, 4000, 500)
        loan_term = st.selectbox("Loan Term (Years)", [3, 4, 5, 6, 7], index=3) # Default to 6 years

        st.header("2. Your Financial Profile")
        credit_score_map = {
            "Excellent: 780+": 800, "Good: 720-779": 750, "Average: 660-719": 690,
            "Fair: 600-659": 630, "Poor: <600": 580
        }
        credit_score_label = st.selectbox("Credit Score", list(credit_score_map.keys()), index=2) # Default to Average
        credit_score_value = credit_score_map[credit_score_label]
        
        monthly_income = st.number_input("Gross Monthly Income ($)", min_value=0, value=6000, step=100, help="Unlocks Affordability Analysis.")
        
        st.header("3. Cost Assumptions")
        vehicle_model_list = list(vehicle_db.df.index)
        # Default to a model with higher depreciation
        default_model = 'BMW 3 Series'
        default_index = vehicle_model_list.index(default_model) if default_model in vehicle_model_list else 0
        vehicle_model = st.selectbox("Vehicle Model", vehicle_model_list, index=default_index)
        
        vehicle_info = vehicle_db.get_vehicle_info(vehicle_model)
        fuel_type = vehicle_info.get('fuel_type', 'Gas')
        
        if fuel_type == 'Gas':
            gas_price = st.number_input("Gas Price ($ / gallon)", min_value=0.0, value=3.50, step=0.10)
            electricity_price = 0.15 # Default
        else: # Electric
            electricity_price = st.number_input("Electricity Price ($ / kWh)", min_value=0.0, value=0.15, step=0.01)
            gas_price = 3.50 # Default

    # --- Calculations ---
    principal = vehicle_price - down_payment
    vehicle_type = "Used" if "Used" in credit_score_label else "New" # Simple assumption
    input_data = {
        'credit_score': [credit_score_value], 'loan_amount_usd': [principal],
        'loan_term_years': [loan_term], 'down_payment_percentage': [down_payment / vehicle_price if vehicle_price > 0 else 0],
        'vehicle_type_Used': [1 if vehicle_type == 'Used' else 0]
    }
    input_df = pd.DataFrame(input_data).reindex(columns=model_cols, fill_value=0)
    predicted_rate = model.predict(input_df)[0]
    emi = calculate_emi(principal, predicted_rate, loan_term)
    total_loan_cost = emi * (loan_term * 12)
    total_interest = total_loan_cost - principal
    
    tco_breakdown = calculate_total_cost_of_ownership(vehicle_info, total_loan_cost, loan_term, gas_price, electricity_price)
    schedule_df = generate_amortization_and_depreciation(principal, predicted_rate, loan_term, emi, vehicle_price, vehicle_info)
    
    # --- UPDATED: More robust calculation for underwater amount ---
    underwater_amounts = (schedule_df['Loan_Balance'] - schedule_df['Car_Value']).clip(lower=0)
    max_underwater = underwater_amounts.max()


    # --- Main Dashboard Layout ---
    main_col1, main_col2 = st.columns([2, 1])

    with main_col1:
        # --- Financial Summary ---
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Financial Summary")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown(f'<div class="metric-card"><div class="title">Monthly Payment</div><div class="value">${emi:,.2f}</div></div>', unsafe_allow_html=True)
        with m_col2:
            st.markdown(f'<div class="metric-card"><div class="title">AI Predicted Rate</div><div class="value">{predicted_rate:.2f}%</div></div>', unsafe_allow_html=True)
        with m_col3:
            st.markdown(f'<div class="metric-card"><div class="title">Total Interest</div><div class="value">${total_interest:,.0f}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # --- TCO and Depreciation Charts Side-by-Side ---
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader(f"Total Cost of Ownership")
            if tco_breakdown:
                labels = list(tco_breakdown.keys())[:-1]
                values = list(tco_breakdown.values())[:-1]
                labels[-1] = "Fuel" if fuel_type == 'Gas' else "Charging"
                
                fig_tco = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, marker_colors=['#2563EB', '#60A5FA', '#93C5FD', '#BFDBFE'], textinfo='percent', textfont_size=12)])
                fig_tco.update_layout(showlegend=True, annotations=[dict(text=f'${tco_breakdown["Total TCO"]:,.0f}', x=0.5, y=0.5, font_size=20, showarrow=False)], margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5), height=400)
                st.plotly_chart(fig_tco, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with chart_col2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.subheader("Depreciation vs. Loan")
            
            # --- UPDATED: Conditional metric display ---
            if max_underwater > 0:
                st.metric("Peak 'Underwater' Amount", f"${max_underwater:,.0f}", help="The highest amount you will owe more than the car is worth.", delta_color="inverse")
            else:
                st.metric("Peak 'Underwater' Amount", f"$0", help="You are never underwater on your loan. Great!")

            fig_dep = go.Figure()
            fig_dep.add_trace(go.Scatter(x=schedule_df['Year'], y=schedule_df['Car_Value'], mode='lines', name='Car Value', line=dict(color='#22C55E', width=3), fill='tozeroy'))
            fig_dep.add_trace(go.Scatter(x=schedule_df['Year'], y=schedule_df['Loan_Balance'], mode='lines', name='Loan Balance', line=dict(color='#2563EB', width=3), fill='tozeroy'))
            
            # Only show red shaded area if user is actually underwater
            if max_underwater > 0:
                fig_dep.add_trace(go.Scatter(
                    x=schedule_df['Year'].tolist() + schedule_df['Year'].tolist()[::-1],
                    y=schedule_df['Loan_Balance'].tolist() + schedule_df['Car_Value'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(239, 68, 68, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip",
                    name='Underwater'
                ))
            fig_dep.update_layout(xaxis_title=None, yaxis_title=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=325, margin=dict(l=0,r=0,b=0,t=20))
            st.plotly_chart(fig_dep, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with main_col2:
        # --- Financial Health and How It Works Cards ---
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Financial Health")
        if monthly_income and monthly_income > 0:
            monthly_tco = tco_breakdown.get('Total TCO', 0) / (loan_term * 12)
            tco_ratio = (monthly_tco / monthly_income) * 100
            status_class, status_icon, status_text = "", "", ""
            if tco_ratio < 15:
                status_class, status_icon, status_text = "good", "✅", "Good"
            elif tco_ratio < 20:
                status_class, status_icon, status_text = "borderline", "⚠️", "Borderline"
            else:
                status_class, status_icon, status_text = "high-risk", "❌", "High-Risk"
            st.markdown(f'<div class="affordability-box {status_class}"><div class="status">{status_icon} {status_text}</div>Your estimated monthly car cost is <b>~{tco_ratio:.0f}%</b> of your income.</div>', unsafe_allow_html=True)
        else:
            st.info("Enter income to see health check.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-card how-it-works">', unsafe_allow_html=True)
        st.subheader("💡 How It Works")
        
        st.markdown("<h6>🧠 AI Interest Rate Model</h6>", unsafe_allow_html=True)
        st.markdown("""
        We use a **Random Forest** model, which acts like a committee of decision-makers to ensure an accurate prediction. It was trained on thousands of loan scenarios to learn the complex relationships between your financial profile and market rates. 
        
        The top factors influencing the prediction are:
        """)
        feature_importances = pd.Series(model.feature_importances_, index=model_cols).sort_values(ascending=False)
        top_features = feature_importances.head(3)
        for feature, _ in top_features.items():
                st.markdown(f"&nbsp;&nbsp;&nbsp;• **{feature.replace('_', ' ').title()}**")

        st.markdown("<h6>⚙️ Total Cost of Ownership</h6>", unsafe_allow_html=True)
        st.markdown("The *true cost* of the car: `Loan + Insurance + Maintenance + Fuel/Charging`.")
        
        st.markdown("<h6>📉 Depreciation Analysis</h6>", unsafe_allow_html=True)
        st.markdown("Compares car value to loan balance. The red shaded area means you are **'underwater'**.")

        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("Application cannot start. Please ensure all required data and model files are present.")
