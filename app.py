import json
from urllib.parse import unquote

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

COOKIE_NAME = "immopark_rt"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 jours

CHART_CONFIG = {
    "displayModeBar": False,
    "staticPlot": True,
    "scrollZoom": False,
    "doubleClick": False,
    "showTips": False,
}

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


# ---------------------------------------------------------------------------
# Supabase : UN client PAR session navigateur (jamais partagé entre utilisateurs)
# ---------------------------------------------------------------------------
def get_client() -> Client:
    if "sb" not in st.session_state:
        st.session_state["sb"] = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"],
        )
    return st.session_state["sb"]


def reset_client():
    st.session_state.pop("sb", None)


# ---------------------------------------------------------------------------
# Persistance de la connexion : cookie navigateur (plus de jetons dans l'URL)
# ---------------------------------------------------------------------------
def write_cookie(value):
    """Écrit (ou efface si value est None) le cookie du refresh token."""
    name = json.dumps(COOKIE_NAME)
    if value:
        cookie_expr = (
            f"{name} + '=' + encodeURIComponent({json.dumps(value)}) + "
            f"'; path=/; max-age={COOKIE_MAX_AGE}; SameSite=Lax' + secure"
        )
    else:
        cookie_expr = f"{name} + '=; path=/; max-age=0; SameSite=Lax' + secure"

    components.html(
        f"""<script>
        try {{
            const d = window.parent.document;
            const secure = window.parent.location.protocol === 'https:' ? '; Secure' : '';
            d.cookie = {cookie_expr};
        }} catch (e) {{}}
        </script>""",
        height=0,
    )


def restore_session_from_cookie(client):
    if st.session_state.get("no_autologin"):
        return None
    raw = st.context.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        resp = client.auth.refresh_session(unquote(raw))
        return resp.session if resp else None
    except Exception:
        return None


def get_current_user():
    client = get_client()
    try:
        session = client.auth.get_session()  # rafraîchit si le jeton a expiré
    except Exception:
        session = None

    if session is None:
        session = restore_session_from_cookie(client)

    if session is None:
        return None

    # Réécrit le cookie à chaque exécution : garde le refresh token à jour
    # même si Supabase l'a renouvelé (rotation).
    write_cookie(session.refresh_token)
    return session.user


def logout():
    try:
        get_client().auth.sign_out({"scope": "local"})  # cet appareil uniquement
    except Exception:
        pass
    reset_client()
    st.session_state["no_autologin"] = True
    st.session_state["clear_cookie"] = True
    st.rerun()


# ---------------------------------------------------------------------------
# Accès aux données
# ---------------------------------------------------------------------------
def load_properties(user_id):
    result = (
        get_client().table("properties")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def create_property(user_id, nom):
    get_client().table("properties").insert(
        default_property(user_id, nom)
    ).execute()


def update_property(property_id, user_id, values):
    """Retourne True seulement si une ligne a réellement été modifiée."""
    result = (
        get_client().table("properties")
        .update(values)
        .eq("id", property_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


CHAMPS_MONTANTS = [
    ("prix_achat_total", "Prix d'achat total avec travaux"),
    ("loyer", "Loyer perçu mensuel"),
    ("credit", "Crédit mensuel"),
    ("assurance", "Assurance mensuelle"),
    ("taxe", "Taxe foncière annuelle"),
    ("copro", "Charges de copropriété mensuelles"),
    ("electricite", "Électricité mensuelle"),
    ("gaz", "Gaz mensuel"),
    ("imprevu", "Imprévu mensuel"),
]


def parse_montant(texte):
    """'1 200,50 €' -> 1200.5 ; vide -> 0.0 ; invalide -> ValueError (jamais 0 silencieux)."""
    s = str(texte or "").strip()
    if s == "":
        return 0.0
    for ch in (" ", "\u00a0", "\u202f", "€"):
        s = s.replace(ch, "")
    s = s.replace(",", ".")
    valeur = float(s)  # lève ValueError si invalide
    if valeur < 0:
        raise ValueError("négatif")
    return valeur


def texte_montant(valeur):
    """Affichage propre dans le champ : 1200.0 -> '1200', 0 -> ''."""
    try:
        f = float(valeur)
    except (TypeError, ValueError):
        return ""
    if f == 0:
        return ""
    return str(int(f)) if f.is_integer() else str(f)


def to_float(value):
    try:
        return float(str(value).replace(",", ".")) if value not in [None, ""] else 0.0
    except ValueError:
        return 0.0


def format_euro(value):
    return f"{value:,.0f} €".replace(",", " ")


def default_property(user_id, nom):
    return {
        "user_id": user_id,
        "nom": nom,
        "prix_achat_total": 0,
        "loyer": 0,
        "credit": 0,
        "assurance": 0,
        "taxe": 0,
        "copro": 0,
        "electricite": 0,
        "gaz": 0,
        "imprevu": 0,
    }


def calcul_bien(bien):
    loyer = to_float(bien.get("loyer"))
    prix_achat_total = to_float(bien.get("prix_achat_total"))
    credit = to_float(bien.get("credit"))
    assurance = to_float(bien.get("assurance"))
    taxe_mensuelle = to_float(bien.get("taxe")) / 12
    copro = to_float(bien.get("copro"))
    electricite = to_float(bien.get("electricite"))
    gaz = to_float(bien.get("gaz"))
    imprevu = to_float(bien.get("imprevu"))

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
    rendement_cashflow = (
        cashflow_annuel / prix_achat_total * 100
        if prix_achat_total > 0
        else 0
    )

    return (
        loyer,
        charges,
        total_charges,
        cashflow,
        cashflow_annuel,
        prix_achat_total,
        rendement_cashflow,
    )


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
        unsafe_allow_html=True,
    )


def afficher_metric(titre, valeur):
    st.markdown(
        f"""
        <div class="small-metric">
            <div class="small-metric-title">{titre}</div>
            <div class="small-metric-value">{valeur}</div>
        </div>
        """,
        unsafe_allow_html=True,
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
        text=[
            f"{r:.2f}%<br>{format_euro(cf)}/mois"
            for r, cf in zip(ratios, cashflows)
        ],
        textposition="auto"
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=20),
        yaxis_title="Ratio annuel (%)",
        xaxis_title="",
        showlegend=False,
        dragmode=False
    )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)

    if ratios_invalides:
        st.caption(
            "Prix d'achat manquant : "
            + ", ".join([x["nom"] for x in ratios_invalides])
        )


def afficher_graphique_cashflows(ratios_biens):
    biens_valides = sorted(ratios_biens, key=lambda x: x["cashflow"], reverse=True)

    if not biens_valides:
        st.info("Aucun bien disponible.")
        return

    noms = [x["nom"] for x in biens_valides]
    cashflows = [x["cashflow"] for x in biens_valides]
    couleurs = [couleur_ratio(i, len(biens_valides)) for i in range(len(biens_valides))]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=noms,
        y=cashflows,
        marker_color=couleurs,
        text=[f"{format_euro(cf)}/mois" for cf in cashflows],
        textposition="auto"
    ))

    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=20),
        yaxis_title="Cashflow mensuel (€)",
        xaxis_title="",
        showlegend=False,
        dragmode=False
    )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    st.plotly_chart(fig, use_container_width=True, config=CHART_CONFIG)


st.title("LMNP Cashflow")

user = get_current_user()

if user is None:
    if st.session_state.pop("clear_cookie", False):
        write_cookie(None)

    client = get_client()
    mode = st.radio(
        "Accès",
        ["Connexion", "Créer un compte", "Mot de passe oublié"],
        horizontal=True
    )

    if mode == "Créer un compte":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe (8 caractères minimum)", type="password")
        password_confirm = st.text_input("Confirmer le mot de passe", type="password")

        if st.button("Créer mon compte"):
            email = email.strip().lower()

            if not email or "@" not in email:
                st.error("Email invalide.")
            elif len(password) < 8:
                st.error("Mot de passe trop court (8 caractères minimum).")
            elif password != password_confirm:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                try:
                    response = client.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    if response.session:
                        st.session_state.pop("no_autologin", None)
                        st.rerun()
                    else:
                        st.success(
                            "Compte créé. Clique sur le lien reçu par email "
                            "pour confirmer, puis connecte-toi."
                        )
                except Exception as e:
                    st.error(f"Erreur création compte : {e}")

    elif mode == "Connexion":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        if st.button("Se connecter"):
            email = email.strip().lower()

            try:
                client.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                st.session_state.pop("no_autologin", None)
                st.rerun()
            except Exception:
                st.error("Email ou mot de passe incorrect.")

    elif mode == "Mot de passe oublié":
        st.caption("Étape 1 : reçois un code par email.")
        email = st.text_input("Email du compte")

        if st.button("Recevoir un code"):
            try:
                client.auth.reset_password_for_email(email.strip().lower())
                st.success("Si le compte existe, un code vient d'être envoyé.")
            except Exception as e:
                st.error(f"Erreur : {e}")

        st.caption("Étape 2 : saisis le code et ton nouveau mot de passe.")
        code = st.text_input("Code reçu par email")
        new_password = st.text_input("Nouveau mot de passe (8 caractères minimum)", type="password")

        if st.button("Changer le mot de passe"):
            if len(new_password) < 8:
                st.error("Mot de passe trop court (8 caractères minimum).")
            else:
                try:
                    client.auth.verify_otp({
                        "email": email.strip().lower(),
                        "token": code.strip(),
                        "type": "recovery",
                    })
                    client.auth.update_user({"password": new_password})
                    st.session_state.pop("no_autologin", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Code invalide ou expiré : {e}")

    st.stop()


if st.button("Déconnexion"):
    logout()

biens = load_properties(user.id)

if len(biens) == 0:
    create_property(user.id, "Bien 1")
    st.rerun()

if st.button("+ Ajouter un bien"):
    create_property(user.id, f"Bien {len(biens) + 1}")
    st.rerun()

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
            (
                loyer,
                charges,
                charges_total,
                cashflow,
                cashflow_annuel,
                prix_achat,
                rendement_cashflow
            ) = calcul_bien(bien)

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

        st.markdown("### Cashflow mensuel par bien")
        afficher_graphique_cashflows(ratios_biens)

        afficher_metric("Cashflow annuel", format_euro(total_cashflow * 12))
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
            fig_pie.update_layout(dragmode=False)
            st.plotly_chart(fig_pie, use_container_width=True, config=CHART_CONFIG)

            st.markdown("### Charges par catégorie")

            fig_bar = px.bar(
                df_charges,
                x="Charge",
                y="Montant",
                text="Montant"
            )
            fig_bar.update_layout(dragmode=False)
            fig_bar.update_xaxes(fixedrange=True)
            fig_bar.update_yaxes(fixedrange=True)
            st.plotly_chart(fig_bar, use_container_width=True, config=CHART_CONFIG)

    tab_index = 1


for i, bien in enumerate(biens):
    with tabs[tab_index + i]:
        (
            loyer,
            charges,
            total_charges,
            cashflow,
            cashflow_annuel,
            prix_achat_total,
            rendement_cashflow
        ) = calcul_bien(bien)

        afficher_cashflow(cashflow)

        if prix_achat_total > 0:
            afficher_metric("Cashflow annuel / prix total", f"{rendement_cashflow:.2f} %")

        # Formulaire : rien n'est envoyé (ni perdu) tant que tu n'appuies pas sur Sauvegarder
        with st.form(key=f"form_{bien['id']}"):
            nouveau_nom = st.text_input(
                "Nom du bien",
                value=bien.get("nom", f"Bien {i + 1}"),
                key=f"nom_{bien['id']}"
            )

            saisies = {}
            for cle, libelle in CHAMPS_MONTANTS:
                if cle == "loyer":
                    st.markdown("### Revenus")
                elif cle == "credit":
                    st.markdown("### Charges principales")
                elif cle == "electricite":
                    st.markdown("### Charges optionnelles")

                saisies[cle] = st.text_input(
                    libelle,
                    value=texte_montant(bien.get(cle)),
                    placeholder="Montant en €",
                    key=f"{cle}_{bien['id']}"
                )

            envoye = st.form_submit_button("💾 Sauvegarder")

        st.caption(
            f"Charges mensuelles : {format_euro(total_charges)} | "
            f"Taxe foncière mensualisée : {format_euro(to_float(bien.get('taxe')) / 12)} | "
            f"Cashflow annuel : {format_euro(cashflow_annuel)}"
        )

        if envoye:
            valeurs, erreurs = {}, []
            for cle, libelle in CHAMPS_MONTANTS:
                try:
                    valeurs[cle] = parse_montant(saisies[cle])
                except ValueError:
                    erreurs.append(libelle)

            if erreurs:
                st.error(
                    "Sauvegarde annulée, montant invalide pour : "
                    + ", ".join(erreurs)
                    + ". Exemple valide : 1200 ou 1 200,50"
                )
            else:
                valeurs["nom"] = nouveau_nom.strip() or f"Bien {i + 1}"
                try:
                    ok = update_property(bien["id"], user.id, valeurs)
                except Exception as e:
                    ok = False
                    st.error(f"Erreur de sauvegarde : {e}")

                if ok:
                    st.success("Bien sauvegardé.")
                    st.rerun()
                else:
                    st.error("La sauvegarde n'a pas été confirmée par la base. Réessaie.")

st.divider()
with st.expander("Exporter mes données (sauvegarde personnelle)"):
    df_export = pd.DataFrame(biens).drop(columns=["user_id"], errors="ignore")
    st.download_button(
        "Télécharger en CSV (compatible Excel)",
        data=df_export.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="immopark_export.csv",
        mime="text/csv",
    )
