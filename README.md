# Organizza Consigli di Classe – Streamlit

App web per organizzare consigli in **tabelle 5×4**:
- ogni **colonna** contiene classi con la **stessa lettera** (es. A: 1A..5A);
- in **ogni riga** (stesso anno) non ci sono **docenti in comune** tra le 4 classi.

## Requisiti
- CSV con colonna **Docente** e colonne classi tipo `1A`, `2B`, … (valido 1..5).
- Python 3.10+ (o usa direttamente Streamlit Community Cloud).

## Avvio locale
```bash
pip install -r requirements.txt
streamlit run app.py
