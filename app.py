import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. SIKKERHED: PASSWORD SYSTEM ---
def check_password():
    """Returnerer True hvis brugeren har indtastet det korrekte password."""
    def password_entered():
        if st.session_state["password"] == "Hestekone1":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Fjern password fra session state efter brug
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Første skærmbillede
        st.title("Måvens' Risteri")
        st.text_input("Indtast kodeord for at starte", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("Måvens' Risteri")
        st.text_input("Indtast kodeord for at starte", type="password", on_change=password_entered, key="password")
        st.error("❌ Forkert kodeord")
        return False
    else:
        return True

# Hvis password er korrekt, kør resten af appen
if check_password():
    
    # --- 2. GOOGLE SHEETS KONFIGURATION ---
    # (Bemærk: Kræver 'st.connection' setup i Streamlit Cloud senere)
    # For nu gemmer vi i session_state, men koden er klar til Sheets
    if 'library' not in st.session_state:
        st.session_state.library = {}

    st.title("☕ Måvens' Private Roast Log & Simulator")

    # --- 3. SIDEBAR: KONTROL ---
    st.sidebar.header("Riste-indstillinger")
    name = st.sidebar.text_input("Navn på rist (f.eks. bønnetype + dato)", "Etiopien G1")
    batch = st.sidebar.slider("Batch size (g)", 100, 1000, 500)
    charge = st.sidebar.slider("Charge Temp (°C)", 150, 250, 220)
    target_time = st.sidebar.number_input("Total tid (min)", 5.0, 20.0, 10.0)
    speed_factor = st.sidebar.selectbox("Simuleringshastighed", [1, 2, 5, 20, 60, "Instant"])
    
    density = st.sidebar.select_slider("Bønnetæthed (1=Blød, 1.2=Hård)", options=[0.8, 1.0, 1.2], value=1.0)

    # --- 4. SIMULERINGSMOTOR ---
    def run_simulation():
        steps = int(target_time * 60)
        bt_data = []
        current_bt = 20.0
        
        for s in range(steps):
            if s < 70:
                current_bt -= (1.8 - (s * 0.025)) * (batch / 500)
            else:
                heat_gain = (charge - current_bt) * (0.002 / density)
                current_bt += heat_gain
            
            bt_data.append(current_bt)
            
            if speed_factor != "Instant":
                time.sleep(1 / (60 * speed_factor)) 
        return bt_data

    # --- 5. GEM FUNKTION (KLAR TIL SHEETS) ---
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Start & Gem Rist"):
        with st.spinner('Simulerer ristning...'):
            result = run_simulation()
            st.session_state.library[name] = {
                "data": result,
                "batch": batch,
                "charge": charge,
                "time": target_time
            }
            st.success(f"✅ Rist '{name}' er gemt!")
            # HER ville koden til at skrive til Google Sheets ligge:
            # conn.update(spreadsheet=URL, data=st.session_state.library)

    if col2.button("Slet Bibliotek"):
        st.session_state.library = {}
        st.rerun()

    # --- 6. SAMMENLIGNING & VISUALISERING ---
    st.header("Sammenligning af profiler (Max 4)")
    all_roasts = list(st.session_state.library.keys())
    selected_roasts = st.multiselect("Vælg riste:", all_roasts, default=all_roasts[:4])

    if selected_roasts:
        fig = go.Figure()
        for r_name in selected_roasts:
            y_data = st.session_state.library[r_name]["data"]
            fig.add_trace(go.Scatter(y=y_data, mode='lines', name=r_name))
        
        fig.update_layout(
            xaxis_title="Tid (sekunder)", 
            yaxis_title="Temperatur (°C)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Vis tekniske detaljer for de valgte riste
        st.subheader("Tekniske Detaljer")
        details = []
        for r_name in selected_roasts:
            d = st.session_state.library[r_name]
            details.append({"Navn": r_name, "Batch (g)": d["batch"], "Charge (C)": d["charge"], "Tid (min)": d["time"]})
        st.table(pd.DataFrame(details))
    else:
        st.info("Log ind og opret en rist for at se data.")