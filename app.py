import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    input {
        font-size: 26px !important;
        height: 58px !important;
        text-align: center !important;
    }

    label {
        font-size: 17px !important;
        font-weight: 600 !important;
    }

    button {
        height: 55px !important;
        font-size: 18px !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 34px !important;
    }
</style>
""", unsafe_allow_html=True)


def montant(label, key):
    valeur = st.text_input(
        label,
        value="",
        placeholder="Ex : 850",
        key=key
    )

    valeur = valeur.replace(",", ".")

    try:
        return float(valeur) if valeur else 0.0
    except ValueError:
        st.warning(f"Montant invalide : {label}")
        return 0.0


st.title("🏠 Suivi cashflow LMNP")

if "biens" not in st.session_state:
    st.session_state.biens = ["Bien 1"]

if st.button("➕ Nouvelle Gestion"):
    nouveau_nom = f"Bien {len(st.session_state.biens) + 1}"
    st.session_state.biens.append(nouveau_nom)

tabs = st.tabs(st.session_state.biens)

for i, tab in enumerate(tabs):
    with tab:
        st.subheader(st.session_state.biens[i])

        st.markdown("### Revenus")

        loyer = montant(
            "Loyer perçu mensuel (€)",
            key=f"loyer_{i}"
        )

        st.markdown("### Charges")

        taxe_fonciere_annuelle = montant(
            "Taxe foncière annuelle (€)",
            key=f"taxe_{i}"
        )

        copro = montant(
            "Charges de copropriété mensuelles (€)",
            key=f"copro_{i}"
        )

        electricite = montant(
            "Électricité mensuelle (€)",
            key=f"electricite_{i}"
        )

        gaz = montant(
            "Gaz mensuel (€)",
            key=f"gaz_{i}"
        )

        credit = montant(
            "Crédit mensuel (€)",
            key=f"credit_{i}"
        )

        assurance = montant(
            "Assurance mensuelle (€)",
            key=f"assurance_{i}"
        )

        imprevu = montant(
            "Imprévu mensuel (€)",
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
