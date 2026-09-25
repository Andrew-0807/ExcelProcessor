import pandas as pd

OUTPUT_COLUMNS = [
    "NR.linie", "Serie", "Numar document", "Data", "Data scadenta",
    "Cod tip Factura", "Nume partener", "Atribut fiscal", "Cod fiscal",
    "Nr.Reg.Com.", "Rezidenta", "Tara", "Judet", "Localitate", "Strada",
    "Numar", "Bloc", "Scara", "Etaj", "Apartament", "Cod postal",
    "Moneda", "Curs", "TVA la incasare", "Taxare inversa",
    "Factura de transport", "Cod agent", "Valoare neta totala",
    "Valoare TVA", "Total document", "Denumire articol", "Cantitate",
    "Tip miscare stoc", "Cont servicii", "Pret de lista",
    "Valoare fara tva", "Val TVA", "Valoare cu TVa", "Optiune TVA",
    "Cota TVA", "Cod TVA SAFT", "Observatie", "Centre de cost",
]
assert len(OUTPUT_COLUMNS) == 43


def process_tehno(df: pd.DataFrame) -> pd.DataFrame:
    # ponytail: detect by column presence — vanzari has nr_iesire, cumparari has pret_vanz
    if "nr_iesire" in df.columns:
        return _vanzari(df)
    elif "pret_vanz" in df.columns:
        return _cumparari(df)
    else:
        raise ValueError(f"Cannot detect file type. Columns found: {list(df.columns)}")


def _vanzari(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~df["tert"].str.contains("CLIENT MARFA|CLIENT  I.T.P", na=False, case=False)].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    dates = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%Y%m%d")
    return pd.DataFrame({
        "NR.linie": [""] * n,
        "Serie": ["FV"] * n,
        "Numar document": df["nr_iesire"].astype(str),
        "Data": dates,
        "Data scadenta": dates,
        "Cod tip Factura": [""] * n,
        "Nume partener": df["tert"],
        "Atribut fiscal": [""] * n,
        "Cod fiscal": df["cod_fiscal"].astype(str).str.replace(r"^RO", "", regex=True),
        "Nr.Reg.Com.": [""] * n,
        "Rezidenta": [""] * n,
        "Tara": [""] * n,
        "Judet": [""] * n,
        "Localitate": [""] * n,
        "Strada": [""] * n,
        "Numar": [""] * n,
        "Bloc": [""] * n,
        "Scara": [""] * n,
        "Etaj": [""] * n,
        "Apartament": [""] * n,
        "Cod postal": [""] * n,
        "Moneda": ["RON"] * n,
        "Curs": [""] * n,
        "TVA la incasare": [""] * n,
        "Taxare inversa": [""] * n,
        "Factura de transport": [""] * n,
        "Cod agent": [""] * n,
        "Valoare neta totala": [""] * n,
        "Valoare TVA": [""] * n,
        "Total document": [""] * n,
        "Denumire articol": df["den_tip"],
        "Cantitate": [1] * n,
        "Tip miscare stoc": [""] * n,
        "Cont servicii": [""] * n,
        "Pret de lista": df["valoare"],
        "Valoare fara tva": [""] * n,
        "Val TVA": [""] * n,
        "Valoare cu TVa": [""] * n,
        "Optiune TVA": ["TAXABILE"] * n,
        "Cota TVA": df["tva_art"],
        "Cod TVA SAFT": [""] * n,
        "Observatie": [""] * n,
        "Centre de cost": [""] * n,
    }, columns=OUTPUT_COLUMNS)


def _cumparari(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    dates = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%Y%m%d")
    # ponytail: any undefined article => 'servicii'; VAT/utility classification
    # is done manually downstream.
    denumire = df["den_tip"].astype(str).replace("Nedefinit", "servicii")
    return pd.DataFrame({
        "NR.linie": [""] * n,
        "Serie": [""] * n,
        "Numar document": df["nr"].astype(str),
        "Data": dates,
        "Data scadenta": dates,
        "Cod tip Factura": [""] * n,
        "Nume partener": df["tert"],
        "Atribut fiscal": [""] * n,
        "Cod fiscal": df["cod_fiscal"].astype(str).str.replace(r"^RO", "", regex=True),
        "Nr.Reg.Com.": [""] * n,
        "Rezidenta": [""] * n,
        "Tara": [""] * n,
        "Judet": [""] * n,
        "Localitate": [""] * n,
        "Strada": [""] * n,
        "Numar": [""] * n,
        "Bloc": [""] * n,
        "Scara": [""] * n,
        "Etaj": [""] * n,
        "Apartament": [""] * n,
        "Cod postal": [""] * n,
        "Moneda": ["RON"] * n,
        "Curs": [""] * n,
        "TVA la incasare": [""] * n,
        "Taxare inversa": [""] * n,
        "Factura de transport": [""] * n,
        "Cod agent": [""] * n,
        "Valoare neta totala": [""] * n,
        "Valoare TVA": [""] * n,
        "Total document": [""] * n,
        "Denumire articol": denumire,
        "Cantitate": [1] * n,
        "Tip miscare stoc": [""] * n,
        "Cont servicii": [""] * n,
        "Pret de lista": df["valoare"],
        "Valoare fara tva": [""] * n,
        "Val TVA": [""] * n,
        "Valoare cu TVa": [""] * n,
        "Optiune TVA": ["TAXABILE"] * n,
        "Cota TVA": [21] * n,
        "Cod TVA SAFT": [""] * n,
        "Observatie": [""] * n,
        "Centre de cost": [""] * n,
    }, columns=OUTPUT_COLUMNS)
