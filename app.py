import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0.5rem;
    padding-left: 0.6rem;
    padding-right: 0.6rem;
}

h1 { font-size: 24px !important; margin-bottom: 0.3rem !important; }

input {
    font-size: 20px !important;
    height: 46px !important;
    text-align: center !important;
}

label {
    font-size: 13px !important;
    font-weight: 600 !important;
}

button {
    height: 46px !important;
    font-size: 15px !important;
}

/* FORCE 2 COLONNES MEME SUR MOBILE */
div[data-testid="column"] {
    width: 50% !important;
    flex: 1 1 50% !important;
}

.cashflow-card {
    padding: 12px;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 6px;
}

.cashflow-title {
    font-size: 14px;
    font-weight: 600;
}

.cashflow-value {
    font-size: 36px;
    font-weight: 800;
}

.pos { background:#e8f7ee; color:#127333; border:2px solid #2ea44f; }
.neg { background:#fdeaea; color:#b42318; border:2px solid #d92d20; }
.neu { background:#f2f4f7; color:#344054; border:2px solid #98a2b3; }

</style>
""", unsafe_allow_html=True)


def montant(label, key):
    val = st.text_input(label, value="", placeholder="€", key=key)
    val = val.replace(",", ".")
    try:
        return float(val) if val else 0.0
    except:
        return 0.0


def cashflow_card(v):
    if v > 0:
        c = "pos"
    elif v < 0:
        c = "neg"
    else:
        c = "neu"

    txt = f"{v:,.0f} €".replace(",", " ")

    st.markdown(f"""
    <div class="cashflow-card {c}">
        <div class="cashflow-title">Cashflow mensuel</div>
        <div class="cashflow-value">{txt}</div>
    </div>
    """, unsafe_allow_html=True)


st.title("🏠 LMNP Cashflow")

if "biens" not in st.session_state:
    st.session_state.biens = ["Bien 1"]

if st.button("➕ Nouvelle Gestion"):
    st.session_state.biens.append(f"Bien {len(st.session_state.biens)+1}")

tabs = st.tabs(st.session_state.biens)

for i, tab in enumerate(tabs):
    with tab:

        # LOYER
        loyer = montant("Loyer perçu mensuel", f"loyer_{i}")

        # PREVIEW
        def g(k): return st.session_state.get(k, "")
        def f(v):
            try: return float(str(v).replace(",", ".")) if v else 0.0
            except: return 0.0

        taxe = f(g(f"taxe_{i}")) / 12
        copro = f(g(f"copro_{i}"))
        credit = f(g(f"credit_{i}"))
        assurance = f(g(f"assurance_{i}"))
        elec = f(g(f"electricite_{i}"))
        gaz = f(g(f"gaz_{i}"))
        imp = f(g(f"imprevu_{i}"))

        charges = taxe + copro + credit + assurance + elec + gaz + imp
        cf = loyer - charges

        cashflow_card(cf)

        # 2 COLONNES
        col1, col2 = st.columns(2)

        with col1:
            taxe_ann = montant("Taxe foncière annuelle", f"taxe_{i}")
            credit = montant("Crédit mensuel", f"credit_{i}")
            elec = montant("Électricité mensuelle", f"electricite_{i}")
            imp = montant("Imprévu mensuel", f"imprevu_{i}")

        with col2:
            copro = montant("Copro mensuelle", f"copro_{i}")
            assurance = montant("Assurance mensuelle", f"assurance_{i}")
            gaz = montant("Gaz mensuel", f"gaz_{i}")

        taxe_m = taxe_ann / 12

        total = taxe_m + copro + credit + assurance + elec + gaz + imp

        st.caption(
            f"Charges : {total:,.0f} € | Taxe mensualisée : {taxe_m:,.0f} €"
            .replace(",", " ")
        )
