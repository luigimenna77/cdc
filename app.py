# app.py
import io
import zipfile
from typing import List, Tuple

import pandas as pd
import streamlit as st

from organizer import (
    load_df, build_class_teacher_map, letters_conflict_graph,
    greedy_group_letters, build_tables, validate_rows
)

st.set_page_config(page_title="Organizza Consigli di Classe", page_icon="🗂️", layout="wide")

st.title("🗂️ Organizza Consigli di Classe – tabelle 5×4")
st.caption("Colonne per lettera; in ogni riga (stesso anno) nessun docente in comune tra le 4 classi.")

with st.sidebar:
    st.header("⚙️ Impostazioni")
    sep = st.selectbox("Separatore CSV", [";", ",", "\\t"], index=0,
                       help="Scegli come è separato il tuo file CSV (default ';').")
    generate_pdf = st.checkbox("Genera anche PDF", value=True)
    st.markdown("---")
    st.write("**Formato atteso:** colonna `Docente` + colonne classi tipo `1A`, `2B`, …")

uploaded = st.file_uploader("Carica il CSV (docenti × classi)", type=["csv"])

def make_zip_of_tables(tables: List[Tuple[int, list, pd.DataFrame]], validation_df: pd.DataFrame) -> bytes:
    """Crea uno ZIP in memoria con tutte le tabelle CSV + riepilogo + verifica."""
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        # tabelle
        for gi, g, tab in tables:
            name = f"tabella_{gi}_{''.join(g)}.csv"
            z.writestr(name, tab.to_csv())
        # riepilogo gruppi
        summary = pd.DataFrame([{"Tabella": gi, "Lettere (colonne)": " | ".join(g), "N. colonne": len(g)} for gi, g, _ in tables])
        z.writestr("riepilogo_gruppi.csv", summary.to_csv(index=False))
        # validazione
        z.writestr("verifica_righe.csv", validation_df.to_csv(index=False))
    return mem.getvalue()

def build_pdf_bytes(tables: List[Tuple[int, list, pd.DataFrame]]) -> bytes:
    """Genera un PDF in memoria con le tabelle (usa reportlab)."""
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet

    mem_pdf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(mem_pdf, pagesize=A4)
    elements = []
    for gi, g, tab in tables:
        elements.append(Paragraph(f"Tabella {gi} – Colonne: {', '.join(g)}", styles['Heading2']))
        data = [["Anno"] + list(g)]
        for y in tab.index:
            row = [str(y)] + [tab.loc[y, L] if pd.notna(tab.loc[y, L]) else "" for L in g]
            data.append(row)
        t = Table(data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('GRID',(0,0),(-1,-1),0.5,colors.black),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))
    doc.build(elements)
    mem_pdf.seek(0)
    return mem_pdf.getvalue()

if uploaded:
    try:
        sep_map = {";": ";", ",": ",", "\\t": "\t"}
        df = load_df(uploaded, sep=sep_map[sep])
        st.success("CSV caricato correttamente.")
        with st.expander("Anteprima dati", expanded=False):
            st.dataframe(df.head(20), use_container_width=True)

        valid_cols, class_to_teachers, year_letter_to_class, complete_letters = build_class_teacher_map(df)
        if not complete_letters:
            st.error("Nessuna lettera presente per tutti i 5 anni. Non posso costruire colonne coerenti 1..5.")
            st.stop()

        conflicts = letters_conflict_graph(complete_letters, class_to_teachers, year_letter_to_class)
        groups = greedy_group_letters(complete_letters, conflicts, max_group_size=4)
        tables = build_tables(groups, year_letter_to_class)
        validation_df = validate_rows(tables, class_to_teachers)

        # RIEPILOGO
        st.subheader("📋 Riepilogo gruppi (tabelle 5×4)")
        summary = pd.DataFrame([
            {"Tabella": gi, "Lettere (colonne)": " | ".join(g), "N. colonne": len(g)}
            for gi, g, _ in tables
        ])
        st.dataframe(summary, use_container_width=True)

        # TABS per ogni tabella
        st.subheader("🧩 Tabelle")
        tabs = st.tabs([f"Tabella {gi} ({' '.join(g)})" for gi, g, _ in tables])
        for tab_obj, (gi, g, tab) in zip(tabs, tables):
            with tab_obj:
                st.markdown(f"**Colonne:** {', '.join(g)}")
                st.dataframe(tab, use_container_width=True)

        # VALIDAZIONE
        st.subheader("✅ Verifica per riga (nessun docente in comune)")
        st.dataframe(validation_df, use_container_width=True)

        # Download ZIP
        zip_bytes = make_zip_of_tables(tables, validation_df)
        st.download_button(
            "⬇️ Scarica ZIP (tabelle + riepilogo + verifica)",
            data=zip_bytes,
            file_name="tabelle_consigli.zip",
            mime="application/zip"
        )

        # PDF opzionale
        if generate_pdf:
            try:
                pdf_bytes = build_pdf_bytes(tables)
                st.download_button(
                    "⬇️ Scarica PDF con tutte le tabelle",
                    data=pdf_bytes,
                    file_name="tabelle_consigli.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.warning(f"PDF non generato (ReportLab non disponibile?): {e}")

    except Exception as e:
        st.error(f"Errore: {e}")
else:
    st.info("Carica un file CSV per iniziare.")
