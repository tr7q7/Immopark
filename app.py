import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding: 0.25rem 0.35rem 0.25rem 0.35rem;
}

h1 {
    font-size: 18px !important;
    margin: 0 !important;
    padding: 0 !important;
}

button {
    height: 34px !important;
    font-size: 12px !important;
    padding: 0 !important;
}

div[data-testid="stTabs"] button {
    height: 30px !important;
    font-size: 12px !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.15rem !important;
}

div[data-testid="column"] {
    width: 50% !important;
    flex: 1 1 50% !important;
    padding: 0 0.12rem !important;
}

label {
    font-size: 11px !important;
    font-weight: 600 !important;
}

input {
    height: 34px !important;
    font-size: 16px !important;
    text-align: center !important;
    padding: 0 !important;
}

.stTextInput {
    margin-bottom: -0.65rem !important;
}

.cashflow-card {
    padding: 6px;
    border-radius: 12px;
    text-align: center;
    margin: 2px 0 4px 0;
}

.cashflow-title {
    font-size: 12px;
    font-weight: 600;
}

.cashflow-value {
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
}

.pos { background:#e8f7ee; color:#127333; border:2px solid #2ea44f; }
.neg { background:#fdeaea; color:#b42318; border:2px solid #d92d20; }
.neu { background:#f2f4f7; color:#344054; border:2px solid #98a2b3; }

div[data-testid="stCaptionContainer"] {
    font-size: 10px !important;
}
</style>
""", unsafe_allow_html=True)


def montant(label, key):
    val = st.text_input(
        label,
        value="",
        placeholder="€",
        key=key
    )
    val = val.replace(",", ".")
    try:
        return float(val) if val else 0.0
    except ValueError:
        return 0.0


def to_float(value):
    try:
        return float(str(value).replace(",", ".")) if value else 0.0
    except ValueError:
        return 0.0


def afficher_cashflow(value):
    if value > 0:
        style = "pos"
    elif value < 0:
        style = "neg"
    else:
        style = "neu"

    txt = f"{value:,.0f} €".replace(",", " ")

    st.markdown(
        f"""
        <div class="cashflow-card {style}">
            <div class="cashflow-title">Cashflow mensuel</div>
            <div class="cashflow-value">{txt}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.title("LMNP Cashflow")

if "biens" not in st.session_state:
    st.session_state.biens = ["Bien 1"]

if st.button("➕ Nouvelle Gestion"):
    st.session_state.biens.append(f"Bien {len(st.session_state.biens) + 1}")

tabs = st.tabs(st.session_state.biens)

for i, tab in enumerate(tabs):
    with tab:
        loyer = montant("Loyer perçu", f"loyer_{i}")

        credit_prev = to_float(st.session_state.get(f"credit_{i}", ""))
        assurance_prev = to_float(st.session_state.get(f"assurance_{i}", ""))
        taxe_prev = to_float(st.session_state.get(f"taxe_{i}", "")) / 12
        copro_prev = to_float(st.session_state.get(f"copro_{i}", ""))
        electricite_prev = to_float(st.session_state.get(f"electricite_{i}", ""))
        gaz_prev = to_float(st.session_state.get(f"gaz_{i}", ""))
        imprevu_prev = to_float(st.session_state.get(f"imprevu_{i}", ""))

        charges_prev = (
            credit_prev
            + assurance_prev
            + taxe_prev
            + copro_prev
            + electricite_prev
            + gaz_prev
            + imprevu_prev
        )

        cashflow = loyer - charges_prev
        afficher_cashflow(cashflow)

        col1, col2 = st.columns(2)

        with col1:
            credit = montant("Crédit mensuel", f"credit_{i}")
            taxe_annuelle = montant("Taxe foncière annuelle", f"taxe_{i}")
            electricite = montant("Électricité", f"electricite_{i}")
            imprevu = montant("Imprévu", f"imprevu_{i}")

        with col2:
            assurance = montant("Assurance mensuelle", f"assurance_{i}")
            copro = montant("Copro mensuelle", f"copro_{i}")
            gaz = montant("Gaz", f"gaz_{i}")

        taxe_mensuelle = taxe_annuelle / 12

        total_charges = (
            credit
            + assurance
            + taxe_mensuelle
            + copro
            + electricite
            + gaz
            + imprevu
        )

        st.caption(
            f"Charges : {total_charges:,.0f} € | Taxe mensuelle : {taxe_mensuelle:,.0f} €"
            .replace(",", " ")
        )
