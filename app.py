import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 0.6rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    h1 {
        font-size: 26px !important;
        margin-bottom: 0.4rem !important;
    }

    h2, h3 {
        margin-top: 0.4rem !important;
        margin-bottom: 0.3rem !important;
    }

    input {
        font-size: 22px !important;
        height: 48px !important;
        text-align: center !important;
    }

    label {
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    button {
        height: 48px !important;
        font-size: 16px !important;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.35rem !important;
    }

    .stTextInput {
        margin-bottom: -0.4rem !important;
    }

    .cashflow-card {
        padding: 14px;
        border-radius: 18px;
        text-align: center;
        margin-bottom: 8px;
    }

    .cashflow-title {
        font-size: 15px;
        font-weight: 600;
        opacity: 0.85;
    }

    .cashflow-value {
        font-size: 42px;
        font-weight: 800;
        line-height: 1.1;
    }

    .cashflow-positive {
        background-color: #e8f7ee;
        color: #127333;
        border: 2px solid #2ea44f;
    }

    .cashflow-negative {
        background-color: #fdeaea;
        color: #b42318;
        border: 2px solid #d92d20;
    }

    .cashflow-neutral {
        background-color: #f2f4f7;
        color: #344054;
        border: 2px solid #98a2b3;
    }
</style>
""", unsafe_allow_html=True)


def montant(label, key):
    valeur = st.text_input(
        label,
        value="",
        placeholder="€",
        key=key
    )

    valeur = valeur.replace(",", ".")

    try:
        return float(valeur) if valeur else 0.0
    except ValueError:
        st.warning(f"Montant invalide : {label}")
        return 0.0


def afficher_cashflow(cashflow):
    if cashflow > 0:
        classe = "cashflow-positive"
    elif cashflow < 0:
        classe = "cashflow-negative"
    else:
        classe = "cashflow-neutral"

    valeur = f"{cashflow:,.2f} €".replace(",", " ")

    st.markdown(
        f"""
        <div class="cashflow-card {classe}">
            <div class="cashflow-title">Cashflow mensuel</div>
            <div class="cashflow-value">{valeur}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.title("🏠 LMNP Cashflow")

if "biens" not in st.session_state:
    st.session_state.biens = ["Bien 1"]

if st.button("➕ Nouvelle Gestion"):
    nouveau_nom = f"Bien {len(st.session_state.biens) + 1}"
    st.session_state.biens.append(nouveau_nom)

tabs = st.tabs(st.session_state.biens)

for i, tab in enumerate(tabs):
    with tab:
        loyer = montant(
            "Loyer perçu mensuel",
            key=f"loyer_{i}"
        )

        taxe_fonciere_annuelle = st.session_state.get(f"taxe_{i}", "")
        copro_val = st.session_state.get(f"copro_{i}", "")
        electricite_val = st.session_state.get(f"electricite_{i}", "")
        gaz_val = st.session_state.get(f"gaz_{i}", "")
        credit_val = st.session_state.get(f"credit_{i}", "")
        assurance_val = st.session_state.get(f"assurance_{i}", "")
        imprevu_val = st.session_state.get(f"imprevu_{i}", "")

        def to_float(v):
            try:
                return float(str(v).replace(",", ".")) if v else 0.0
            except ValueError:
                return 0.0

        taxe_mensuelle_preview = to_float(taxe_fonciere_annuelle) / 12

        charges_preview = (
            taxe_mensuelle_preview
            + to_float(copro_val)
            + to_float(electricite_val)
            + to_float(gaz_val)
            + to_float(credit_val)
            + to_float(assurance_val)
            + to_float(imprevu_val)
        )

        cashflow_preview = loyer - charges_preview

        afficher_cashflow(cashflow_preview)

        col1, col2 = st.columns(2)

        with col1:
            taxe_fonciere_annuelle = montant(
                "Taxe foncière annuelle",
                key=f"taxe_{i}"
            )

            electricite = montant(
                "Électricité mensuelle",
                key=f"electricite_{i}"
            )

            credit = montant(
                "Crédit mensuel",
                key=f"credit_{i}"
            )

            imprevu = montant(
                "Imprévu mensuel",
                key=f"imprevu_{i}"
            )

        with col2:
            copro = montant(
                "Copro mensuelle",
                key=f"copro_{i}"
            )

            gaz = montant(
                "Gaz mensuel",
                key=f"gaz_{i}"
            )

            assurance = montant(
                "Assurance mensuelle",
                key=f"assurance_{i}"
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

        st.caption(
            f"Charges mensuelles : {charges_totales:,.2f} € | "
            f"Taxe foncière mensualisée : {taxe_mensuelle:,.2f} €"
            .replace(",", " ")
        )
