import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Suivi cashflow LMNP")

# Initialisation
if "biens" not in st.session_state:
    st.session_state.biens = ["Bien 1"]

# Bouton nouvel onglet
if st.button("➕ Nouvelle Gestion"):
    nouveau_nom = f"Bien {len(st.session_state.biens) + 1}"
    st.session_state.biens.append(nouveau_nom)

# Création des onglets
tabs = st.tabs(st.session_state.biens)

for i, tab in enumerate(tabs):
    with tab:
        st.subheader(st.session_state.biens[i])

        st.markdown("### Revenus")
        loyer = st.number_input(
            "Loyer perçu mensuel (€)",
            min_value=0.0,
            step=10.0,
            key=f"loyer_{i}"
        )

        st.markdown("### Charges mensuelles")

        taxe_fonciere_annuelle = st.number_input(
            "Taxe foncière annuelle (€)",
            min_value=0.0,
            step=50.0,
            key=f"taxe_{i}"
        )

        copro = st.number_input(
            "Charges de copropriété mensuelles (€)",
            min_value=0.0,
            step=10.0,
            key=f"copro_{i}"
        )

        electricite = st.number_input(
            "Électricité mensuelle (€)",
            min_value=0.0,
            step=10.0,
            key=f"electricite_{i}"
        )

        gaz = st.number_input(
            "Gaz mensuel (€)",
            min_value=0.0,
            step=10.0,
            key=f"gaz_{i}"
        )

        credit = st.number_input(
            "Crédit mensuel (€)",
            min_value=0.0,
            step=10.0,
            key=f"credit_{i}"
        )

        assurance = st.number_input(
            "Assurance mensuelle (€)",
            min_value=0.0,
            step=5.0,
            key=f"assurance_{i}"
        )

        imprevu = st.number_input(
            "Imprévu mensuel (€)",
            min_value=0.0,
            step=10.0,
            key=f"imprevu_{i}"
        )

        taxe_mensuelle = taxe_fonciere_annuelle / 12

        charges_totales = (
            taxe_mensuelle
            + copro
            + electricite
            + gaz
            + credit
            + assurance
            + imprevu
        )

        cashflow = loyer - charges_totales

        st.markdown("---")

        st.metric(
            "Cashflow mensuel",
            f"{cashflow:,.2f} €".replace(",", " ")
        )

        st.caption(
            f"Charges mensuelles totales : {charges_totales:,.2f} € "
            f"dont taxe foncière mensualisée : {taxe_mensuelle:,.2f} €"
            .replace(",", " ")
        )
