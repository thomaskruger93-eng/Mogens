import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- 1. SIKKERHED: PASSWORD SYSTEM ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Hestekone1":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
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
    if 'library' not in st.session_state:
        st.session_state.library = {}

    st.title("☕ Måvens' Præcisions-simulator v9.0")

    # --- 2. SIDEBAR: INDSTILLINGER ---
    st.sidebar.header("Riste-indstillinger")
    name = st.sidebar.text_input("Navn på rist", "Batch #1")
    batch = st.sidebar.slider("Batch size (g)", 100, 1000, 500)
    charge = st.sidebar.slider("Charge Temp (°C)", 150, 250, 210)
    
    st.sidebar.subheader("Fase-tider (minutter)")
    dry_time = st.sidebar.slider("Tørrefase (20°C -> 150°C)", 2.0, 8.0, 4.0)
    maillard_time = st.sidebar.slider("Maillard (150°C -> 200°C)", 1.0, 6.0, 3.5)
    dev_time = st.sidebar.slider("Udvikling (efter FC)", 0.5, 5.0, 1.5)
    
    st.sidebar.subheader("Slut-temperatur")
    drop_temp = st.sidebar.slider("Drop Temp (°C)", 200, 230, 205)
    
    total_time = dry_time + maillard_time + dev_time
    dtr = (dev_time / total_time) * 100
    st.sidebar.info(f"Samlet tid: {total_time:.2f} min | DTR: {dtr:.1f}%")

    speed_factor = st.sidebar.selectbox("Simuleringshastighed", ["Instant", 1, 5, 20, 60])
    density = st.sidebar.select_slider("Bønnetæthed", options=[0.8, 1.0, 1.2], value=1.0)

    # --- 3. SIMULERINGSMOTOR ---
    def run_simulation():
        steps_dry = int(dry_time * 60)
        steps_maillard = int(maillard_time * 60)
        steps_dev = int(dev_time * 60)
        bt_data = []
        current_bt = 20.0
        
        # Fase 1: Tørring
        for s in range(steps_dry):
            if s < 60:
                current_bt -= (1.5 - (s * 0.02)) * (batch / 500)
            else:
                current_bt += (150 - current_bt) / (steps_dry - s)
            bt_data.append(current_bt)
            if speed_factor != "Instant": time.sleep(1 / (60 * speed_factor))

        # Fase 2: Maillard
        start_m = current_bt
        for s in range(steps_maillard):
            current_bt += (200 - start_m) / steps_maillard
            bt_data.append(current_bt)
            if speed_factor != "Instant": time.sleep(1 / (60 * speed_factor))

        # Fase 3: Udvikling
        start_d = current_bt
        for s in range(steps_dev):
            current_bt += (drop_temp - start_d) / steps_dev
            bt_data.append(current_bt)
            if speed_factor != "Instant": time.sleep(1 / (60 * speed_factor))
        return bt_data

    # --- 4. GEM FUNKTION ---
    if st.sidebar.button("Simulér & Gem Profil"):
        with st.spinner('Beregner...'):
            data = run_simulation()
            st.session_state.library[name] = {
                "data": data, "dry": dry_time, "maillard": maillard_time, 
                "dev": dev_time, "total": total_time, "drop": drop_temp, "dtr": dtr
            }

    if st.sidebar.button("Slet alt bibliotek"):
        st.session_state.library = {}
        st.rerun()

    # --- 5. VISUALISERING ---
    all_roasts = list(st.session_state.library.keys())
    selected_roasts = st.multiselect("Vælg op til 4 riste at sammenligne:", all_roasts, default=all_roasts[:4])

    if selected_roasts:
        fig = go.Figure()
        for r_name in selected_roasts:
            r = st.session_state.library[r_name]
            fig.add_trace(go.Scatter(y=r["data"], name=f"{r_name} ({r['drop']}°C)"))
        
        # Markør-linjer for faser på den første valgte rist
        f = st.session_state.library[selected_roasts[0]]
        fig.add_vline(x=f['dry']*60, line_dash="dot", line_color="gray", annotation_text="150°C")
        fig.add_vline(x=(f['dry']+f['maillard'])*60, line_dash="dot", line_color="gray", annotation_text="FC Start")
        
        fig.update_layout(xaxis_title="Sekunder", yaxis_title="Bean Temp °C")
        st.plotly_chart(fig, use_container_width=True)

        # --- 6. SMAGS-ANALYSATOR ---
        st.header("👅 Smagsprofil Vurdering")
        for n in selected_roasts:
            r = st.session_state.library[n]
            with st.expander(f"Se vurdering for: {n}"):
                # Syre analyse
                if r['drop'] < 205: syre = "Høj og frisk (Citrus, Grønne æbler)"
                elif r['drop'] < 212: syre = "Balanceret og moden (Stenfrugt, Bær)"
                else: syre = "Lav og dæmpet (Kakao, Røg)"
                
                # Krop analyse
                if r['maillard'] > 4: krop = "Kraftig og cremet"
                elif r['maillard'] < 2.5: krop = "Let og te-agtig"
                else: krop = "Medium/Sirupsagtig"

                st.write(f"**Karakter:** En {krop.lower()} kaffe med {syre.lower()} syre.")
                if r['dtr'] < 12: st.warning("⚠️ Risiko for græsset/underudviklet smag.")
                if r['total'] > 14: st.warning("⚠️ Risiko for 'bagt' smag (flad sødme).")
                if not (r['dtr'] < 12 or r['total'] > 14): st.success("✅ Profilen ser balanceret ud.")
    else:
        st.info("Indtast password og opret en rist for at starte.")
