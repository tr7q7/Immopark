import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="centered"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 520px;
}

h1 {
    font-size: 26px !important;
    text-align: center;
}

input {
    height: 48px !important;
    font-size: 22px !important;
    text-align: center !important;
}

label {
    font-size: 15px !important;
    font-weight: 600 !important;
}

button {
    width: 100% !important;
    height: 46px !important;
    font-size: 16px !important;
}

.cashflow-card {
    padding: 18px;
    border-radius: 18px;
    text-align: center;
    margin: 14px 0;
}

.cashflow-title {
    font-size: 16px;
    font-weight: 600;
}

.cashflow-value {
    font-size: 44px;
    font-weight: 800;
    line-height: 1.1;
}

.pos {
    background: #e8f7ee;
    color: #127333;
    border: 2px solid #2ea44f;
}

.neg {
    background: #fdeaea;
    color: #b42318;
    border: 2px solid #d92d20;
}

.neu {
    background: #f2f4f7;
    color: #344054;
    border: 2px solid #98a2b3;
}
</style>
""", unsafe_allow_html=True)


def to_float(value):
    try:
        return float(str(value).replace(",", ".")) if value else 0.0
    except ValueError:
        return 0.0


def montant(label, key):
    value = st.text_input(
        label,
        value="",
        placeholder="Montant en €",
        key=key
    )
    return to_float(value)


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
        loyer = montant("Loyer perçu mensuel", f"loyer_{i}")

        credit_prev = to_float(st.session_state.get(f"credit_{i}", ""))
        assurance_prev = to_float(st.session_state.get(f"assurance_{i}", ""))
        taxe_prev = to_float(st.session_state.get(f"taxe_{i}", "")) / 12
        copro_prev = to_float(st.session_state.get(f"copro_{i}", ""))
        electricite_prev = to_float(st.session_state.get(f"electricite_{i}", ""))
        gaz_prev = to_float(st.session_state.get(f"gaz_{i}", ""))
        imprevu_prev = to_float(st.session_state.get(f"imprevu_{i}", ""))

        total_prev = (
            credit_prev
            + assurance_prev
            + taxe_prev
            + copro_prev
            + electricite_prev
            + gaz_prev
            + imprevu_prev
        )

        afficher_cashflow(loyer - total_prev)

        st.markdown("### Charges principales")

        credit = montant("Crédit mensuel", f"credit_{i}")
        assurance = montant("Assurance mensuelle", f"assurance_{i}")
        taxe_annuelle = montant("Taxe foncière annuelle", f"taxe_{i}")
        copro = montant("Charges de copropriété mensuelles", f"copro_{i}")

        st.markdown("### Charges optionnelles")

        electricite = montant("Électricité mensuelle", f"electricite_{i}")
        gaz = montant("Gaz mensuel", f"gaz_{i}")
        imprevu = montant("Imprévu mensuel", f"imprevu_{i}")

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
            f"Charges mensuelles : {total_charges:,.0f} € | "
            f"Taxe foncière mensualisée : {taxe_mensuelle:,.0f} €"
            .replace(",", " ")
        )
