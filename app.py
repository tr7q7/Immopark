import streamlit as st
import json
import os
import hashlib
import secrets
import smtplib
import ssl
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from email.message import EmailMessage

DATA_FILE = "lmnp_data.json"
SESSION_DURATION = 3600

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="centered"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0.8rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 560px;
}

h1 {
    font-size: 25px !important;
    text-align: center;
    margin-bottom: 0.4rem;
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
    height: 44px !important;
    font-size: 15px !important;
}

.top-right-button {
    position: fixed;
    top: 8px;
    right: 10px;
    z-index: 9999;
}

.top-right-button button {
    width: auto !important;
    height: 30px !important;
    font-size: 11px !important;
    padding: 2px 8px !important;
    opacity: 0.75;
}

.bottom-plus {
    position: fixed;
    bottom: 18px;
    right: 18px;
    z-index: 9999;
}

.bottom-plus button {
    width: 54px !important;
    height: 54px !important;
    border-radius: 50% !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    padding: 0 !important;
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

.small-metric {
    padding: 12px;
    border-radius: 14px;
    background: #f8f9fb;
    border: 1px solid #e5e7eb;
    text-align: center;
    margin-bottom: 10px;
}

.small-metric-title {
    font-size: 13px;
    color: #667085;
    font-weight: 600;
}

.small-metric-value {
    font-size: 25px;
    font-weight: 800;
    color: #101828;
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


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_session(data, email):
    token = secrets.token_urlsafe(32)
    data["users"][email]["session_token"] = token
    data["users"][email]["session_expiry"] = time.time() + SESSION_DURATION
    save_data(data)
    st.query_params["session"] = token
    return token


def get_user_from_session(data):
    token = st.query_params.get("session")

    if not token:
        return None

    for email, user_data in data["users"].items():
        if user_data.get("session_token") == token:
            expiry = user_data.get("session_expiry", 0)

            if time.time() < expiry:
                return email
            else:
                user_data["session_token"] = None
                user_data["session_expiry"] = None
                save_data(data)
                st.query_params.clear()
                return None

    return None


def logout(data, email):
    if email in data["users"]:
        data["users"][email]["session_token"] = None
        data["users"][email]["session_expiry"] = None
        save_data(data)

    st.query_params.clear()


def to_float(value):
    try:
        return float(str(value).replace(",", ".")) if value else 0.0
    except ValueError:
        return 0.0


def format_euro(value):
    return f"{value:,.0f} €".replace(",", " ")


def default_bien(nom):
    return {
        "nom": nom,
        "prix_achat_total": "",
        "loyer": "",
        "credit": "",
        "assurance": "",
        "taxe": "",
        "copro": "",
        "electricite": "",
        "gaz": "",
        "imprevu": ""
    }


def calcul_bien(bien):
    loyer = to_float(bien.get("loyer", 0))
    prix_achat_total = to_float(bien.get("prix_achat_total", 0))
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
    cashflow_annuel = cashflow * 12
    rendement_cashflow = (cashflow_annuel / prix_achat_total * 100) if prix_achat_total > 0 else 0

    return loyer, charges, total_charges, cashflow, cashflow_annuel, prix_achat_total, rendement_cashflow


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


def afficher_metric(titre, valeur):
    st.markdown(
        f"""
        <div class="small-metric">
            <div class="small-metric-title">{titre}</div>
            <div class="small-metric-value">{valeur}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def couleur_ratio(index, total):
    if total <= 1:
        return "rgb(34,197,94)"

    t = index / (total - 1)

    r1, g1, b1 = 34, 197, 94
    r2, g2, b2 = 251, 146, 60

    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)

    return f"rgb({r},{g},{b})"


def afficher_graphique_ratios(ratios_biens):
    ratios_valides = [x for x in ratios_biens if x["prix_achat"] > 0]
    ratios_invalides = [x for x in ratios_biens if x["prix_achat"] <= 0]

    if not ratios_valides:
        st.info("Renseigne les prix d'achat pour afficher le graphique des ratios.")
        return

    ratios_valides = sorted(ratios_valides, key=lambda x: x["ratio"], reverse=True)

    noms = [x["nom"] for x in ratios_valides]
    ratios = [x["ratio"] for x in ratios_valides]
    cashflows = [x["cashflow"] for x in ratios_valides]
    couleurs = [couleur_ratio(i, len(ratios_valides)) for i in range(len(ratios_valides))]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=noms,
        y=ratios,
        marker_color=couleurs,
        text=[f"{r:.2f}%<br>{format_euro(cf)}/mois" for r, cf in zip(ratios, cashflows)],
        textposition="auto",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Ratio cashflow/prix achat : %{y:.2f}%<br>"
            "Cashflow mensuel : %{customdata}<extra></extra>"
        ),
        customdata=[format_euro(cf) for cf in cashflows]
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=20),
        yaxis_title="Ratio annuel (%)",
        xaxis_title="",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    if ratios_invalides:
        st.caption(
            "Prix d'achat manquant : "
            + ", ".join([x["nom"] for x in ratios_invalides])
        )


def smtp_is_configured():
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"]
    return all(k in st.secrets for k in required)


def send_reset_email(to_email, reset_code):
    if not smtp_is_configured():
        return False

    msg = EmailMessage()
    msg["Subject"] = "Réinitialisation mot de passe - LMNP Cashflow"
    msg["From"] = st.secrets["SMTP_FROM"]
    msg["To"] = to_email

    msg.set_content(
        f"""
Bonjour,

Voici votre code de réinitialisation :

{reset_code}

Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.

LMNP Cashflow
"""
    )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        st.secrets["SMTP_HOST"],
        int(st.secrets["SMTP_PORT"]),
        context=context
    ) as server:
        server.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASSWORD"])
        server.send_message(msg)

    return True


data = load_data()

if "reset_email" not in st.session_state:
    st.session_state.reset_email = None

logged_user = get_user_from_session(data)

st.title("LMNP Cashflow")

if logged_user is None:
    mode = st.radio(
        "Accès",
        ["Connexion", "Créer un compte", "Mot de passe oublié"],
        horizontal=True
    )

    if mode == "Créer un compte":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        password_confirm = st.text_input("Confirmer le mot de passe", type="password")

        if st.button("Créer mon compte"):
            email = email.strip().lower()

            if not email or "@" not in email:
                st.error("Email invalide.")
            elif not password:
                st.error("Mot de passe obligatoire.")
            elif password != password_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            elif email in data["users"]:
                st.error("Un compte existe déjà avec cet email.")
            else:
                data["users"][email] = {
                    "password": hash_password(password),
                    "reset_code": None,
                    "session_token": None,
                    "session_expiry": None,
                    "biens": [default_bien("Bien 1")]
                }
                create_session(data, email)
                st.rerun()

    elif mode == "Connexion":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        if st.button("Se connecter"):
            email = email.strip().lower()

            if email not in data["users"]:
                st.error("Compte introuvable.")
            elif data["users"][email]["password"] != hash_password(password):
                st.error("Mot de passe incorrect.")
            else:
                create_session(data, email)
                st.rerun()

    elif mode == "Mot de passe oublié":
        email = st.text_input("Email du compte")

        if st.button("Recevoir un code"):
            email = email.strip().lower()

            if email not in data["users"]:
                st.error("Compte introuvable.")
            else:
                reset_code = str(secrets.randbelow(900000) + 100000)
                data["users"][email]["reset_code"] = reset_code
                save_data(data)

                try:
                    sent = send_reset_email(email, reset_code)
                    st.session_state.reset_email = email

                    if sent:
                        st.success("Code envoyé par email.")
                    else:
                        st.warning(f"SMTP non configuré. Code de test : {reset_code}")
                except Exception:
                    st.session_state.reset_email = email
                    st.warning(f"Impossible d'envoyer l'email. Code de test : {reset_code}")

        if st.session_state.reset_email:
            st.markdown("### Réinitialiser le mot de passe")

            code = st.text_input("Code reçu")
            new_password = st.text_input("Nouveau mot de passe", type="password")
            new_password_confirm = st.text_input("Confirmer le nouveau mot de passe", type="password")

            if st.button("Changer le mot de passe"):
                email_reset = st.session_state.reset_email

                if email_reset not in data["users"]:
                    st.error("Compte introuvable.")
                elif code != data["users"][email_reset].get("reset_code"):
                    st.error("Code incorrect.")
                elif not new_password:
                    st.error("Mot de passe obligatoire.")
                elif new_password != new_password_confirm:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    data["users"][email_reset]["password"] = hash_password(new_password)
                    data["users"][email_reset]["reset_code"] = None
                    save_data(data)

                    st.session_state.reset_email = None
                    st.success("Mot de passe modifié. Tu peux te connecter.")

    st.stop()


user = logged_user
user_data = data["users"][user]

if "biens" not in user_data or len(user_data["biens"]) == 0:
    user_data["biens"] = [default_bien("Bien 1")]
    save_data(data)

st.markdown('<div class="top-right-button">', unsafe_allow_html=True)
if st.button("Déconnexion"):
    logout(data, user)
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

biens = user_data["biens"]

st.markdown('<div class="bottom-plus">', unsafe_allow_html=True)
if st.button("+"):
    user_data["biens"].append(default_bien(f"Bien {len(user_data['biens']) + 1}"))
    save_data(data)
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

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
        ratios_biens = []

        for bien in biens:
            loyer, charges, charges_total, cashflow, cashflow_annuel, prix_achat, rendement_cashflow = calcul_bien(bien)

            total_loyer += loyer
            total_charges += charges_total
            total_cashflow += cashflow

            ratios_biens.append({
                "nom": bien.get("nom", "Bien"),
                "ratio": rendement_cashflow,
                "cashflow": cashflow,
                "prix_achat": prix_achat
            })

            for nom_charge, montant in charges.items():
                charges_globales[nom_charge] = charges_globales.get(nom_charge, 0) + montant

        afficher_cashflow(total_cashflow, "Cashflow global mensuel")

        st.markdown("### Ratio cashflow / prix d'achat")
        afficher_graphique_ratios(ratios_biens)

        afficher_metric("Loyer mensuel", format_euro(total_loyer))
        afficher_metric("Loyer annuel", format_euro(total_loyer * 12))
        afficher_metric("Charges mensuelles", format_euro(total_charges))

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
    if "prix_achat_total" not in bien:
        bien["prix_achat_total"] = ""

    with tabs[tab_index + i]:
        loyer, charges, total_charges, cashflow, cashflow_annuel, prix_achat_total, rendement_cashflow = calcul_bien(bien)

        afficher_cashflow(cashflow)

        if prix_achat_total > 0:
            afficher_metric("Cashflow annuel / prix total", f"{rendement_cashflow:.2f} %")

        nouveau_nom = st.text_input(
            "Nom du bien",
            value=bien.get("nom", f"Bien {i + 1}"),
            key=f"nom_{i}"
        )

        prix_achat_input = st.text_input(
            "Prix d'achat total avec travaux",
            value=str(bien.get("prix_achat_total", "")),
            placeholder="Montant total en €",
            key=f"prix_achat_total_{i}"
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
            f"Taxe foncière mensualisée : {format_euro(to_float(bien.get('taxe', 0)) / 12)} | "
            f"Cashflow annuel : {format_euro(cashflow_annuel)}"
        )

        if st.button("💾 Sauvegarder", key=f"save_{i}"):
            bien["nom"] = nouveau_nom if nouveau_nom else f"Bien {i + 1}"
            bien["prix_achat_total"] = prix_achat_input
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
