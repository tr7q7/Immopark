import streamlit as st
import json
import os
import hashlib
import pandas as pd
import plotly.express as px

DATA_FILE = "lmnp_data.json"

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
    max-width: 560px;
}

h1 {
    font-size: 26px !important;
    text-align: center;
}

input {
    height: 48px !important;
    font-size: 21px !important;
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


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def to_float(value):
    try:
        return float(str(value).replace(",", ".")) if value else 0.0
    except ValueError:
        return 0.0


def format_euro(value):
    return f"{value:,.0f} €".replace(",", " ")


def calcul_bien(bien):
    loyer = to_float(bien.get("loyer", 0))
    credit = to_float(bien.get("credit", 0))
    assurance = to_float(bien.get("assurance", 0))
    taxe_mensuelle = to_float(bien.get("taxe", 0)) / 12
    copro = to_float(bien.get("copro", 0))
    electricite = to_float(bien.get("electricite", 0))
    gaz = to_float(bien.get("gaz", 0))
    imprevu = to_float(bien.get("imprevu", 0))

    charges = {
        "Crédit": credit,
        "Assurance": assurance,
        "Taxe foncière": taxe_mensuelle,
        "Copropriété": copro,
        "Électricité": electricite,
        "Gaz": gaz,
        "Imprévu": imprevu,
    }

    total_charges = sum(charges.values())
    cashflow = loyer - total_charges

    return loyer, charges, total_charges, cashflow


def afficher_cashflow(value, titre="Cashflow mensuel"):
    if value > 0:
        style = "pos"
    elif value < 0:
        style = "neg"
    else:
        style = "neu"

    st.markdown(
        f"""
        <div class="cashflow-card {style}">
            <div class="cashflow-title">{titre}</div>
            <div class="cashflow-value">{format_euro(value)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def default_bien(nom):
    return {
        "nom": nom,
        "loyer": "",
        "credit": "",
        "assurance": "",
        "taxe": "",
        "copro": "",
        "electricite": "",
        "gaz": "",
        "imprevu": ""
    }


data = load_data()

if "logged_user" not in st.session_state:
    st.session_state.logged_user = None

st.title("LMNP Cashflow")

if st.session_state.logged_user is None:
    st.markdown("### Connexion")

    mode = st.radio(
        "Mode",
        ["Connexion", "Créer un compte"],
        horizontal=True
    )

    username = st.text_input("Nom d'utilisateur")
    pin = st.text_input("Code PIN", type="password")

    if mode == "Créer un compte":
        if st.button("Créer mon compte"):
            if not username or not pin:
                st.error("Renseigne un nom d'utilisateur et un PIN.")
            elif username in data["users"]:
                st.error("Ce compte existe déjà.")
            else:
                data["users"][username] = {
                    "pin": hash_pin(pin),
                    "biens": [default_bien("Bien 1")]
                }
                save_data(data)
                st.session_state.logged_user = username
                st.rerun()

    if mode == "Connexion":
        if st.button("Se connecter"):
            if username not in data["users"]:
                st.error("Compte introuvable.")
            elif data["users"][username]["pin"] != hash_pin(pin):
                st.error("PIN incorrect.")
            else:
                st.session_state.logged_user = username
                st.rerun()

    st.stop()


user = st.session_state.logged_user
user_data = data["users"][user]

if "biens" not in user_data or len(user_data["biens"]) == 0:
    user_data["biens"] = [default_bien("Bien 1")]
    save_data(data)

col_a, col_b = st.columns(2)

with col_a:
    if st.button("➕ Nouveau bien"):
        user_data["biens"].append(default_bien(f"Bien {len(user_data['biens']) + 1}"))
        save_data(data)
        st.rerun()

with col_b:
    if st.button("Déconnexion"):
        st.session_state.logged_user = None
        st.rerun()


biens = user_data["biens"]

tab_names = []
if len(biens) > 1:
    tab_names.append("Dashboard")

tab_names += [bien["nom"] for bien in biens]

tabs = st.tabs(tab_names)

tab_index = 0

if len(biens) > 1:
    with tabs[0]:
        total_loyer = 0
        total_charges = 0
        total_cashflow = 0
        charges_globales = {}

        for bien in biens:
            loyer, charges, charges_total, cashflow = calcul_bien(bien)
            total_loyer += loyer
            total_charges += charges_total
            total_cashflow += cashflow

            for nom_charge, montant in charges.items():
                charges_globales[nom_charge] = charges_globales.get(nom_charge, 0) + montant

        afficher_cashflow(total_cashflow, "Cashflow global mensuel")

        st.metric("Loyers mensuels", format_euro(total_loyer))
        st.metric("Charges mensuelles", format_euro(total_charges))

        df_charges = pd.DataFrame({
            "Charge": list(charges_globales.keys()),
            "Montant": list(charges_globales.values())
        })

        df_charges = df_charges[df_charges["Montant"] > 0]

        if not df_charges.empty:
            st.markdown("### Répartition des charges globales")
            fig_pie = px.pie(
                df_charges,
                names="Charge",
                values="Montant",
                hole=0.35
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("### Charges par catégorie")
            fig_bar = px.bar(
                df_charges,
                x="Charge",
                y="Montant",
                text="Montant"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Renseigne les charges pour afficher les graphiques.")

    tab_index = 1


for i, bien in enumerate(biens):
    with tabs[tab_index + i]:
        loyer, charges, total_charges, cashflow = calcul_bien(bien)

        afficher_cashflow(cashflow)

        nouveau_nom = st.text_input(
            "Nom du bien",
            value=bien.get("nom", f"Bien {i + 1}"),
            key=f"nom_{i}"
        )

        st.markdown("### Revenus")

        loyer_input = st.text_input(
            "Loyer perçu mensuel",
            value=str(bien.get("loyer", "")),
            placeholder="Montant en €",
            key=f"loyer_{i}"
        )

        st.markdown("### Charges principales")

        credit_input = st.text_input(
            "Crédit mensuel",
            value=str(bien.get("credit", "")),
            placeholder="Montant en €",
            key=f"credit_{i}"
        )

        assurance_input = st.text_input(
            "Assurance mensuelle",
            value=str(bien.get("assurance", "")),
            placeholder="Montant en €",
            key=f"assurance_{i}"
        )

        taxe_input = st.text_input(
            "Taxe foncière annuelle",
            value=str(bien.get("taxe", "")),
            placeholder="Montant annuel en €",
            key=f"taxe_{i}"
        )

        copro_input = st.text_input(
            "Charges de copropriété mensuelles",
            value=str(bien.get("copro", "")),
            placeholder="Montant en €",
            key=f"copro_{i}"
        )

        st.markdown("### Charges optionnelles")

        electricite_input = st.text_input(
            "Électricité mensuelle",
            value=str(bien.get("electricite", "")),
            placeholder="Montant en €",
            key=f"electricite_{i}"
        )

        gaz_input = st.text_input(
            "Gaz mensuel",
            value=str(bien.get("gaz", "")),
            placeholder="Montant en €",
            key=f"gaz_{i}"
        )

        imprevu_input = st.text_input(
            "Imprévu mensuel",
            value=str(bien.get("imprevu", "")),
            placeholder="Montant en €",
            key=f"imprevu_{i}"
        )

        st.caption(
            f"Charges mensuelles : {format_euro(total_charges)} | "
            f"Taxe foncière mensualisée : {format_euro(to_float(bien.get('taxe', 0)) / 12)}"
        )

        if st.button("💾 Sauvegarder", key=f"save_{i}"):
            bien["nom"] = nouveau_nom if nouveau_nom else f"Bien {i + 1}"
            bien["loyer"] = loyer_input
            bien["credit"] = credit_input
            bien["assurance"] = assurance_input
            bien["taxe"] = taxe_input
            bien["copro"] = copro_input
            bien["electricite"] = electricite_input
            bien["gaz"] = gaz_input
            bien["imprevu"] = imprevu_input

            save_data(data)
            st.success("Bien sauvegardé.")
            st.rerun()
