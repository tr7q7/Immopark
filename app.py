import streamlit as st

st.set_page_config(
    page_title="LMNP Cashflow",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Suivi cashflow LMNP")

st.markdown("### Vue rapide")

col1, col2 = st.columns(2)

with col1:
    st.metric("Cashflow mensuel", "0 €")

with col2:
    st.metric("Cashflow annuel", "0 €")

st.markdown("---")

st.markdown("### Actions")

if st.button("Ajouter un bien"):
    st.write("Formulaire à venir")
