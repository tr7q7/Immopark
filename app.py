import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

SESSION_DURATION_SECONDS = 3600

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


@st.cache_resource
def init_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )


supabase = init_supabase()


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


def save_session(session):
    st.query_params["access_token"] = session.access_token
    st.query_params["refresh_token"] = session.refresh_token


def clear_session():
    st.query_params.clear()


def get_current_user():
    access_token = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token")

    if not access_token or not refresh_token:
        return None

    try:
        supabase.auth.set_session(access_token, refresh_token)
        user_response = supabase.auth.get_user()
        return user_response.user
    except Exception:
        clear_session()
        return None


def create_profile_if_needed(user):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user.id)
        .execute()
    )

    if not existing.data:
        supabase.table("profiles").insert({
            "id": user.id,
            "email": user.email
        }).execute()


def load_properties(user_id):
    result = (
        supabase.table("properties")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def create_property(user_id, nom):
    supabase.table("properties").insert(
        default_property(user_id, nom)
    ).execute()


def update_property(property_id, values):
    supabase.table("properties").update(values).eq("id", property_id).execute()


st.title("LMNP Cashflow")

user = get_current_user()

if user is None:
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
            else:
                try:
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    if response.session:
                        save_session(response.session)
                        create_profile_if_needed(response.user)
                        create_property(response.user.id, "Bien 1")
                        st.rerun()
                    else:
                        st.success(
                            "Compte créé. Vérifie ton email si Supabase demande une confirmation."
                        )
                except Exception as e:
                    st.error(f"Erreur création compte : {e}")

    elif mode == "Connexion":
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        if st.button("Se connecter"):
            email = email.strip().lower()

            try:
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                save_session(response.session)
                create_profile_if_needed(response.user)

                properties = load_properties(response.user.id)
                if len(properties) == 0:
                    create_property(response.user.id, "Bien 1")

                st.rerun()

            except Exception:
                st.error("Email ou mot de passe incorrect.")

    elif mode == "Mot de passe oublié":
        email = st.text_input("Email du compte")

        if st.button("Recevoir un email de réinitialisation"):
            email = email.strip().lower()

            try:
                supabase.auth.reset_password_email(email)
                st.success("Email de réinitialisation envoyé si le compte existe.")
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.stop()


create_profile_if_needed(user)

st.markdown('<div class="top-right-button">', unsafe_allow_html=True)
if st.button("Déconnexion"):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    clear_session()
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

biens = load_properties(user.id)

if len(biens) == 0:
    create_property(user.id, "Bien 1")
    st.rerun()

st.markdown('<div class="bottom-plus">', unsafe_allow_html=True)
if st.button("+"):
    create_property(user.id, f"Bien {len(biens) + 1}")
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

        nouveau_nom = st.text_input(
            "Nom du bien",
            value=bien.get("nom", f"Bien {i + 1}"),
            key=f"nom_{bien['id']}"
        )

        prix_achat_input = st.text_input(
            "Prix d'achat total avec travaux",
            value=str(bien.get("prix_achat_total") or ""),
            placeholder="Montant total en €",
            key=f"prix_achat_total_{bien['id']}"
        )

        st.markdown("### Revenus")

        loyer_input = st.text_input(
            "Loyer perçu mensuel",
            value=str(bien.get("loyer") or ""),
            placeholder="Montant en €",
            key=f"loyer_{bien['id']}"
        )

        st.markdown("### Charges principales")

        credit_input = st.text_input(
            "Crédit mensuel",
            value=str(bien.get("credit") or ""),
            placeholder="Montant en €",
            key=f"credit_{bien['id']}"
        )

        assurance_input = st.text_input(
            "Assurance mensuelle",
            value=str(bien.get("assurance") or ""),
            placeholder="Montant en €",
            key=f"assurance_{bien['id']}"
        )

        taxe_input = st.text_input(
            "Taxe foncière annuelle",
            value=str(bien.get("taxe") or ""),
            placeholder="Montant annuel en €",
            key=f"taxe_{bien['id']}"
        )

        copro_input = st.text_input(
            "Charges de copropriété mensuelles",
            value=str(bien.get("copro") or ""),
            placeholder="Montant en €",
            key=f"copro_{bien['id']}"
        )

        st.markdown("### Charges optionnelles")

        electricite_input = st.text_input(
            "Électricité mensuelle",
            value=str(bien.get("electricite") or ""),
            placeholder="Montant en €",
            key=f"electricite_{bien['id']}"
        )

        gaz_input = st.text_input(
            "Gaz mensuel",
            value=str(bien.get("gaz") or ""),
            placeholder="Montant en €",
            key=f"gaz_{bien['id']}"
        )

        imprevu_input = st.text_input(
            "Imprévu mensuel",
            value=str(bien.get("imprevu") or ""),
            placeholder="Montant en €",
            key=f"imprevu_{bien['id']}"
        )

        st.caption(
            f"Charges mensuelles : {format_euro(total_charges)} | "
            f"Taxe foncière mensualisée : {format_euro(to_float(bien.get('taxe')) / 12)} | "
            f"Cashflow annuel : {format_euro(cashflow_annuel)}"
        )

        if st.button("💾 Sauvegarder", key=f"save_{bien['id']}"):
            update_property(
                bien["id"],
                {
                    "nom": nouveau_nom if nouveau_nom else f"Bien {i + 1}",
                    "prix_achat_total": to_float(prix_achat_input),
                    "loyer": to_float(loyer_input),
                    "credit": to_float(credit_input),
                    "assurance": to_float(assurance_input),
                    "taxe": to_float(taxe_input),
                    "copro": to_float(copro_input),
                    "electricite": to_float(electricite_input),
                    "gaz": to_float(gaz_input),
                    "imprevu": to_float(imprevu_input),
                }
            )

            st.success("Bien sauvegardé.")
            st.rerun()
