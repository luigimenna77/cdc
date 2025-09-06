# organizer.py
import re
from itertools import combinations
from typing import Dict, List, Set, Tuple

import pandas as pd

def parse_class(col: str):
    """Ritorna (anno:int, lettera:str) se col è del tipo '1A'..'5Z', altrimenti None."""
    m = re.fullmatch(r"([1-5])([A-Z])", str(col).strip())
    if m:
        return int(m.group(1)), m.group(2)
    return None

def load_df(file, sep=";") -> pd.DataFrame:
    df = pd.read_csv(file, sep=sep)
    # normalizza colonna Docente
    if "Docente" not in df.columns:
        for c in df.columns:
            if str(c).strip().lower() == "docente":
                df = df.rename(columns={c: "Docente"})
                break
    if "Docente" not in df.columns:
        raise ValueError("Colonna 'Docente' non trovata nel CSV.")
    df["Docente"] = df["Docente"].astype(str).str.strip()
    return df

def build_class_teacher_map(df: pd.DataFrame):
    """Ritorna (valid_cols, class_to_teachers, year_letter_to_class, complete_letters)."""
    class_cols = [c for c in df.columns if c != "Docente"]
    valid_cols = [c for c in class_cols if parse_class(c) is not None]

    class_to_teachers: Dict[str, Set[str]] = {}
    for c in valid_cols:
        mask = df[c].astype(str).str.strip().ne("") & df[c].notna()
        teachers = set(df.loc[mask, "Docente"].astype(str).str.strip())
        class_to_teachers[c] = teachers

    parsed = {c: parse_class(c) for c in valid_cols}
    year_letter_to_class = {parsed[c]: c for c in valid_cols}
    letters = sorted({ltr for (_, ltr) in year_letter_to_class.keys()})
    complete_letters = [ltr for ltr in letters if all((y, ltr) in year_letter_to_class for y in range(1, 6))]
    return valid_cols, class_to_teachers, year_letter_to_class, complete_letters

def letters_conflict_graph(letters: List[str],
                           class_to_teachers: Dict[str, Set[str]],
                           year_letter_to_class: Dict[Tuple[int, str], str]) -> Dict[str, Set[str]]:
    """Conflitto tra due lettere se in almeno un anno condividono docenti."""
    conflicts = {L: set() for L in letters}
    for i, L1 in enumerate(letters):
        for L2 in letters[i+1:]:
            for y in range(1, 6):
                c1 = year_letter_to_class[(y, L1)]
                c2 = year_letter_to_class[(y, L2)]
                if class_to_teachers[c1] & class_to_teachers[c2]:
                    conflicts[L1].add(L2)
                    conflicts[L2].add(L1)
                    break
    return conflicts

def greedy_group_letters(letters: List[str], conflicts: Dict[str, Set[str]], max_group_size: int = 4) -> List[List[str]]:
    """Euristica greedy: lettere più “difficili” prima, poi nel primo gruppo compatibile."""
    letters_sorted = sorted(letters, key=lambda L: len(conflicts[L]), reverse=True)
    groups: List[List[str]] = []
    for L in letters_sorted:
        placed = False
        for g in groups:
            if len(g) < max_group_size and all(L not in conflicts[other] for other in g):
                g.append(L)
                placed = True
                break
        if not placed:
            groups.append([L])
    return groups

def build_tables(groups: List[List[str]], year_letter_to_class: Dict[Tuple[int, str], str]):
    """Ritorna lista di tuple (gi, lettere_del_gruppo, tabella_df 5x|g|)."""
    tables = []
    for gi, g in enumerate(groups, start=1):
        data = []
        for y in range(1, 6):
            row = {"Anno": y}
            for L in g:
                row[L] = year_letter_to_class.get((y, L), "")
            data.append(row)
        tab = pd.DataFrame(data).set_index("Anno")
        tables.append((gi, g, tab))
    return tables

def validate_rows(tables, class_to_teachers: Dict[str, Set[str]]) -> pd.DataFrame:
    def row_ok(class_names: List[str]) -> bool:
        cl = [c for c in class_names if c]
        for c1, c2 in combinations(cl, 2):
            if class_to_teachers[c1] & class_to_teachers[c2]:
                return False
        return True
    rows = []
    for gi, g, tab in tables:
        for y in tab.index:
            ok = row_ok([tab.loc[y, L] for L in g])
            rows.append({"Tabella": gi, "Anno": y, "Valida (nessun docente in comune)": "Sì" if ok else "No"})
    return pd.DataFrame(rows)
