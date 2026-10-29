import html
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
.block-container { padding: 0.8rem 0.8rem 4rem; max-width: 560px; }
h1 { font-size: 24px !important; text-align: center; margin-bottom: 0.4rem; }
h3 { font-size: 18px !important; margin-top: 1.2rem !important; }

/* Champs : 18px minimum évite le zoom automatique sur iPhone */
input { height: 48px !important; font-size: 18px !important; text-align: center !important; }
label { font-size: 15px !important; font-weight: 600 !important; }

/* Boutons : grandes cibles tactiles */
.stButton button, .stFormSubmitButton button, .stDownloadButton button {
    min-height: 48px; font-size: 15px; width: 100%;
}

/* Les colonnes restent côte à côte sur mobile (utilisées uniquement pour la barre du haut) */
div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0.5rem !important; }
div[data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }

/* Onglets : faciles à toucher, défilement horizontal natif */
button[data-baseweb="tab"] { padding: 10px 14px !important; font-size: 15px !important; }

.cashflow-card { padding: 16px; border-radius: 18px; text-align: center; margin: 12px 0; }
.cashflow-title { font-size: 15px; font-weight: 600; }
.cashflow-value { font-size: 40px; font-weight: 800; line-height: 1.1; }
.pos { background: #e8f7ee; color: #127333; border: 2px solid #2ea44f; }
.neg { background: #fdeaea; color: #b42318; border: 2px solid #d92d20; }
.neu { background: #f2f4f7; color: #344054; border: 2px solid #98a2b3; }

.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }
.small-metric { padding: 10px; border-radius: 14px; background: #f8f9fb; border: 1px solid #e5e7eb; text-align: center; margin-bottom: 10px; }
.metric-grid .small-metric { margin-bottom: 0; }
.small-metric-title { font-size: 12px; color: #667085; font-weight: 600; }
.small-metric-value { font-size: 22px; font-weight: 800; color: #101828; }
.small-metric-value.neg-text { color: #d92d20; }

/* Camemberts par bien : bande qui se fait glisser vers la gauche */
.pie-strip {
    display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch; padding: 4px 2px 12px; margin: 0 -2px;
}
.pie-card {
    flex: 0 0 84%; scroll-snap-align: start; box-sizing: border-box;
    background: #f8f9fb; border: 1px solid #e5e7eb; border-radius: 16px; padding: 12px;
}
.pie-title { font-weight: 700; font-size: 16px; text-align: center; color: #101828; overflow-wrap: anywhere; }
.pie-sub { font-size: 12px; color: #667085; text-align: center; margin-bottom: 4px; }
.pie-card svg { width: 100%; max-width: 210px; display: block; margin: 0 auto 6px; }
.legend-row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 3px 0; color: #344054; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.legend-name { flex: 1; }
.legend-val { font-weight: 600; white-space: nowrap; }
.pie-alert { margin-top: 8px; font-size: 13px; font-weight: 600; color: #d92d20; text-align: center; }
.pie-empty { font-size: 13px; color: #667085; text-align: center; padding: 30px 6px; }
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


ROUGE = "#d92d20"
TEXTE_NEUTRE = "#344054"

COULEURS_CHARGES = {
    "Crédit": "#2563eb",
    "Assurance": "#7c3aed",
    "Taxe foncière": "#f59e0b",
    "Copropriété": "#0891b2",
    "Électricité": "#eab308",
    "Gaz": "#f97316",
    "Imprévu": "#64748b",
    "Cashflow": "#22c55e",
}


def afficher_metric(titre, valeur):
    st.markdown(
        f'<div class="small-metric"><div class="small-metric-title">{titre}</div>'
        f'<div class="small-metric-value">{valeur}</div></div>',
        unsafe_allow_html=True,
    )


def afficher_metrics_grid(items):
    """items = [(titre, valeur_texte, en_rouge), ...] affichés en 2 colonnes."""
    cases = []
    for titre, valeur, en_rouge in items:
        cls = " neg-text" if en_rouge else ""
        cases.append(
            f'<div class="small-metric"><div class="small-metric-title">{titre}</div>'
            f'<div class="small-metric-value{cls}">{valeur}</div></div>'
        )
    st.markdown('<div class="metric-grid">' + "".join(cases) + "</div>", unsafe_allow_html=True)


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


def plage_y(valeurs):
    """Axe Y avec de la marge pour que les libellés (au-dessus / en dessous des barres) ne soient pas coupés."""
    bas = min([0] + valeurs)
    haut = max([0] + valeurs)
    ecart = (haut - bas) or 1
    return [bas - ecart * 0.3 if bas < 0 else 0, haut + ecart * 0.3]


def mettre_en_forme_barres(fig, noms, valeurs, titre_y):
    fig.add_hline(y=0, line_width=1, line_color="#98a2b3")
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=30, b=20),
        yaxis_title=titre_y,
        xaxis_title="",
        showlegend=False,
        dragmode=False,
    )
    fig.update_xaxes(
        fixedrange=True,
        tickangle=-30 if len(noms) > 3 else 0,
        automargin=True,
    )
    fig.update_yaxes(fixedrange=True, range=plage_y(valeurs), zeroline=False)


def afficher_graphique_ratios(ratios_biens):
    valides = sorted(
        [x for x in ratios_biens if x["prix_achat"] > 0],
        key=lambda x: x["ratio"],
        reverse=True,
    )
    sans_prix = [x for x in ratios_biens if x["prix_achat"] <= 0]
    sans_prix_negatifs = [x for x in sans_prix if x["cashflow"] < 0]
    sans_prix_autres = [x for x in sans_prix if x["cashflow"] >= 0]

    if not valides and not sans_prix_negatifs:
        st.info("Renseigne les prix d'achat pour afficher le graphique des ratios.")
        return

    nb_positifs = len([x for x in valides if x["cashflow"] >= 0])
    noms, ratios, couleurs, textes, couleurs_textes = [], [], [], [], []
    rang = 0

    for x in valides:
        negatif = x["cashflow"] < 0
        if negatif:
            couleurs.append(ROUGE)
        else:
            couleurs.append(couleur_ratio(rang, nb_positifs))
            rang += 1
        noms.append(x["nom"])
        ratios.append(x["ratio"])
        textes.append(f"{x['ratio']:.2f}%<br>{format_euro(x['cashflow'])}/mois")
        couleurs_textes.append(ROUGE if negatif else TEXTE_NEUTRE)

    # Biens en déficit mais sans prix d'achat : visibles quand même (barre à 0, montant en rouge)
    for x in sans_prix_negatifs:
        noms.append(x["nom"])
        ratios.append(0)
        couleurs.append(ROUGE)
        textes.append(f"n/d<br>{format_euro(x['cashflow'])}/mois")
        couleurs_textes.append(ROUGE)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=noms,
        y=ratios,
        marker_color=couleurs,
        text=textes,
        textposition="outside",
        textfont=dict(color=couleurs_textes, size=12),
        cliponaxis=False,
    ))
    mettre_en_forme_barres(fig, noms, ratios, "Ratio annuel (%)")
    st.plotly_chart(fig, config=CHART_CONFIG)

    manquants = [x["nom"] for x in sans_prix_negatifs + sans_prix_autres]
    if manquants:
        st.caption("Prix d'achat manquant : " + ", ".join(manquants))


def afficher_graphique_cashflows(ratios_biens):
    biens_tries = sorted(ratios_biens, key=lambda x: x["cashflow"], reverse=True)

    if not biens_tries:
        st.info("Aucun bien disponible.")
        return

    nb_positifs = len([x for x in biens_tries if x["cashflow"] >= 0])
    noms, cashflows, couleurs, couleurs_textes = [], [], [], []
    rang = 0

    for x in biens_tries:
        negatif = x["cashflow"] < 0
        if negatif:
            couleurs.append(ROUGE)
        else:
            couleurs.append(couleur_ratio(rang, nb_positifs))
            rang += 1
        noms.append(x["nom"])
        cashflows.append(x["cashflow"])
        couleurs_textes.append(ROUGE if negatif else TEXTE_NEUTRE)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=noms,
        y=cashflows,
        marker_color=couleurs,
        text=[f"{format_euro(cf)}/mois" for cf in cashflows],
        textposition="outside",
        textfont=dict(color=couleurs_textes, size=12),
        cliponaxis=False,
    ))
    mettre_en_forme_barres(fig, noms, cashflows, "Cashflow mensuel (€)")
    st.plotly_chart(fig, config=CHART_CONFIG)


def donut_svg(parts, total, centre_valeur, centre_rouge):
    """Anneau SVG : chaque part = (nom, montant, couleur). total = ce que représente 100 % de l'anneau."""
    r = 15.9155  # circonférence = 100 -> les longueurs de tirets sont directement des %
    elements = [
        f'<circle cx="21" cy="21" r="{r}" fill="none" stroke="#e5e7eb" stroke-width="6"/>'
    ]
    decalage = 0.0
    for _nom, montant, couleur in parts:
        if montant <= 0 or total <= 0:
            continue
        pct = montant / total * 100
        elements.append(
            f'<circle cx="21" cy="21" r="{r}" fill="none" stroke="{couleur}" stroke-width="6" '
            f'stroke-dasharray="{pct:.3f} {100 - pct:.3f}" stroke-dashoffset="{-decalage:.3f}" '
            f'transform="rotate(-90 21 21)"/>'
        )
        decalage += pct
    couleur_centre = ROUGE if centre_rouge else "#101828"
    elements.append(
        '<text x="21" y="19.5" text-anchor="middle" font-size="3.2" fill="#667085">Cashflow</text>'
        f'<text x="21" y="25.5" text-anchor="middle" font-size="5" font-weight="800" '
        f'fill="{couleur_centre}">{html.escape(centre_valeur)}</text>'
    )
    return '<svg viewBox="0 0 42 42" role="img">' + "".join(elements) + "</svg>"


def afficher_repartition_loyers(biens):
    """Un camembert par bien : 100 % = le loyer, on en retire chaque charge ; le reste = cashflow.
    Si les charges dépassent le loyer, l'anneau représente les charges et le déficit est signalé en rouge."""
    cartes = []

    for bien in biens:
        loyer, charges, total_charges, cashflow, _ca, _prix, _rdt = calcul_bien(bien)
        nom = html.escape(str(bien.get("nom") or "Bien"))

        if loyer <= 0:
            corps = '<div class="pie-empty">Renseigne le loyer de ce bien pour voir la répartition.</div>'
            sous_titre = ""
        else:
            sous_titre = f'<div class="pie-sub">Loyer : {format_euro(loyer)} / mois</div>'
            parts = [
                (n, m, COULEURS_CHARGES.get(n, "#94a3b8"))
                for n, m in charges.items() if m > 0
            ]
            deficit = cashflow < 0
            if cashflow > 0:
                parts.append(("Cashflow", cashflow, COULEURS_CHARGES["Cashflow"]))

            total_anneau = total_charges if deficit else loyer
            corps = donut_svg(parts, total_anneau, format_euro(cashflow), deficit)

            for n, m, couleur in parts:
                corps += (
                    f'<div class="legend-row"><span class="legend-dot" style="background:{couleur}"></span>'
                    f'<span class="legend-name">{html.escape(n)}</span>'
                    f'<span class="legend-val">{format_euro(m)} · {m / loyer * 100:.0f} %</span></div>'
                )

            if deficit:
                corps += (
                    f'<div class="pie-alert">Charges = {total_charges / loyer * 100:.0f} % du loyer '
                    f'· déficit de {format_euro(-cashflow)} / mois</div>'
                )

        cartes.append(f'<div class="pie-card"><div class="pie-title">{nom}</div>{sous_titre}{corps}</div>')

    st.markdown('<div class="pie-strip">' + "".join(cartes) + "</div>", unsafe_allow_html=True)
    st.caption("← Glisse vers la gauche pour voir les autres biens")


def activer_clavier_numerique():
    """Affiche le clavier numérique sur mobile pour les champs de montants."""
    libelles = json.dumps([libelle for _cle, libelle in CHAMPS_MONTANTS])
    components.html(
        f"""<script>
        const libelles = {libelles};
        function patch() {{
            try {{
                window.parent.document.querySelectorAll('input').forEach(el => {{
                    const l = el.getAttribute('aria-label');
                    if (l && libelles.includes(l)) {{ el.setAttribute('inputmode', 'decimal'); }}
                }});
            }} catch (e) {{}}
        }}
        patch();
        try {{
            new MutationObserver(patch).observe(window.parent.document.body, {{childList: true, subtree: true}});
        }} catch (e) {{}}
        </script>""",
        height=0,
    )


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


biens = load_properties(user.id)

if len(biens) == 0:
    create_property(user.id, "Bien 1")
    st.rerun()

col_ajout, col_deco = st.columns(2)
with col_ajout:
    if st.button("＋ Ajouter un bien"):
        create_property(user.id, f"Bien {len(biens) + 1}")
        st.rerun()
with col_deco:
    if st.button("Déconnexion"):
        logout()

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

        st.markdown("### Répartition du loyer par bien")
        afficher_repartition_loyers(biens)

        st.markdown("### Cashflow mensuel par bien")
        afficher_graphique_cashflows(ratios_biens)

        afficher_metrics_grid([
            ("Cashflow annuel", format_euro(total_cashflow * 12), total_cashflow < 0),
            ("Loyer mensuel", format_euro(total_loyer), False),
            ("Loyer annuel", format_euro(total_loyer * 12), False),
            ("Charges mensuelles", format_euro(total_charges), False),
        ])

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
                hole=0.35,
                color="Charge",
                color_discrete_map=COULEURS_CHARGES,
            )
            fig_pie.update_traces(textinfo="percent")
            fig_pie.update_layout(
                dragmode=False,
                height=360,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.05, x=0.5, xanchor="center"),
            )
            st.plotly_chart(fig_pie, config=CHART_CONFIG)

            st.markdown("### Charges par catégorie")

            fig_bar = px.bar(
                df_charges,
                x="Charge",
                y="Montant",
                text="Montant",
                color="Charge",
                color_discrete_map=COULEURS_CHARGES,
            )
            fig_bar.update_traces(texttemplate="%{text:.0f} €", textposition="outside", cliponaxis=False)
            fig_bar.update_layout(
                dragmode=False,
                height=320,
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False,
                xaxis_title="",
            )
            fig_bar.update_xaxes(fixedrange=True, tickangle=-30, automargin=True)
            fig_bar.update_yaxes(fixedrange=True)
            st.plotly_chart(fig_bar, config=CHART_CONFIG)

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

activer_clavier_numerique()
