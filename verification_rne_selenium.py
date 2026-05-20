import os, re, time
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ── CHARGER VARIABLES D'ENVIRONNEMENT ──────────────────────────
load_dotenv()

# ── CONFIGURATION ──────────────────────────────────────────────
SERVER       = "DALI-HEZZI\\LOCALSQL"
BASE         = "maghrebia_dq"
TIMEOUT      = 25
RNE_URL      = "https://www.registre-entreprises.tn/rne-public/#/extrait-registre"
LOGIN_URL    = "https://www.registre-entreprises.tn/rne-public/#/login"
RNE_EMAIL    = os.getenv("RNE_EMAIL")
RNE_PASSWORD = os.getenv("RNE_PASSWORD")
# ───────────────────────────────────────────────────────────────

def normaliser_mf(mf_brut):
    if not mf_brut or str(mf_brut).strip() in ("","None","nan"):
        return None, "NULL"
    mf = str(mf_brut).strip().upper()
    if re.match(r'^(\d{7}[A-Z])\d{3}[A-Z]$', mf): return mf[:8], f"Forme longue -> {mf[:8]}"
    if re.match(r'^0(\d{7}[A-Z])$', mf):           return mf[1:], f"Zero supprime -> {mf[1:]}"
    if re.match(r'^\d{7}[A-Z]$', mf):              return mf, "Forme normale"
    return None, f"Format inconnu ({mf})"

def creer_driver():
    opt = Options()
    opt.add_argument("--lang=fr-FR")
    opt.add_argument("--window-size=1280,900")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("detach", True)
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opt)

def se_connecter(driver):
    wait = WebDriverWait(driver, TIMEOUT)
    driver.get(LOGIN_URL)
    time.sleep(5)
    el = wait.until(EC.element_to_be_clickable((By.ID, "mat-input-0")))
    el.clear(); el.send_keys(RNE_EMAIL)
    el2 = driver.find_element(By.ID, "mat-input-1")
    el2.clear(); el2.send_keys(RNE_PASSWORD)
    time.sleep(0.5)
    btn = driver.find_element(By.XPATH, "//button[contains(normalize-space(),'Login')]")
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(7)
    return "login" not in driver.current_url.lower()

def activer_personne_morale(driver):
    try:
        checked = driver.execute_script(
            "return document.querySelector('mat-slide-toggle input[type=checkbox]').checked;")
        if not checked:
            bar = driver.find_element(By.CSS_SELECTOR, ".mat-slide-toggle-bar")
            driver.execute_script("arguments[0].click();", bar)
            time.sleep(1.5)
    except: pass

def extraire_raison_sociale(driver):
    """Extrait raison sociale FR + AR depuis la page RNE."""
    rs_fr, rs_ar = "", ""
    try:
        lignes = [l.strip() for l in
                  driver.find_element(By.TAG_NAME,"body").text.split('\n')
                  if l.strip()]
        for i, l in enumerate(lignes):
            ll = l.lower()
            if "raison sociale (fr)" in ll or "raison sociale(fr)" in ll:
                val = l.split(":",1)[1].strip() if ":" in l else ""
                rs_fr = val if val else (lignes[i+1] if i+1 < len(lignes) else "")
            if "raison sociale (ar)" in ll or "raison sociale(ar)" in ll:
                val = l.split(":",1)[1].strip() if ":" in l else ""
                rs_ar = val if val else (lignes[i+1] if i+1 < len(lignes) else "")
    except: pass

    if rs_fr and rs_ar: return f"{rs_ar} | {rs_fr}"
    return rs_fr or rs_ar or ""

def verifier_mf(driver, mf_norm):
    wait = WebDriverWait(driver, TIMEOUT)
    driver.get(RNE_URL)
    time.sleep(5)
    activer_personne_morale(driver)
    time.sleep(1)

    champ = wait.until(EC.element_to_be_clickable((By.ID, "mat-input-2")))
    champ.click(); time.sleep(0.3)
    champ.send_keys(Keys.CONTROL + "a"); champ.send_keys(Keys.DELETE)
    champ.clear(); time.sleep(0.2)
    champ.send_keys(mf_norm); time.sleep(0.5)

    btn = driver.find_element(By.XPATH, "//button[contains(normalize-space(),'Suivant')]")
    url_avant    = driver.current_url
    taille_avant = len(driver.find_element(By.TAG_NAME, "body").text)
    driver.execute_script("arguments[0].click();", btn)

    for _ in range(15):
        time.sleep(1)
        try:
            url_now  = driver.current_url
            body_now = driver.find_element(By.TAG_NAME, "body").text
            if url_now != url_avant: time.sleep(2); break
            if len(body_now) != taille_avant: time.sleep(1); break
        except: pass

    body     = driver.find_element(By.TAG_NAME, "body").text
    body_low = body.lower()
    url_fin  = driver.current_url

    if "veuillez entrer un identifiant unique valide" in body_low:
        return "INVALIDE_FORMAT", "Format non reconnu par le RNE", ""

    if url_fin != url_avant or "#/extrait-registre/" in url_fin:
        return "TROUVE", "Present dans le RNE", extraire_raison_sociale(driver)

    ko = ["aucun resultat","aucune entreprise","introuvable","not found",
          "matricule invalide","identifiant invalide","aucune donnee",
          "n'existe pas","non trouve","inexistant"]
    for k in ko:
        if k in body_low:
            return "NON_TROUVE", "Absent du RNE", ""

    ok_kw = ["raison sociale","denomination","siege social","activite",
             "forme juridique","date immatriculation","capital social"]
    for k in ok_kw:
        if k in body_low:
            return "TROUVE", "Present dans le RNE", extraire_raison_sociale(driver)

    return "AMBIGU", f"Page {len(body)} chars", ""


# ══════════════════════════════════════════════════════════════
print("="*65)
print("  Verification MF -- RNE (Selenium v14)")
print(f"  Compte : {RNE_EMAIL}")
print("="*65)

# ── CHARGEMENT MF DEPUIS SQL SERVER ───────────────────────────
# Charge TOUS les identifiants de type MF depuis toutes les tables
# Pour vérifier lesquels existent ou non dans le RNE

engine = None
df_all = pd.DataFrame()

print("\n  Connexion SQL Server...")
try:
    engine = create_engine(
        "mssql+pyodbc://" + SERVER + "/" + BASE +
        "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    )
    with engine.connect() as c:
        print("  SQL Server OK")

    # Requête UNION sur TOUTES les tables contenant un identifiant MF
    query = """
    SELECT 'table_assure' AS source_table, police,
           identifiant AS mf_original, prenom_nom AS nom
    FROM table_assure
    WHERE identifiant IS NOT NULL
      AND LEN(identifiant) IN (8,9,12)
      AND identifiant NOT LIKE '%[^A-Za-z0-9]%'
      AND (
        identifiant LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR identifiant LIKE '0[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR identifiant LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z][0-9][0-9][0-9][A-Z]'
      )

    UNION ALL

    SELECT 'CRM_Maladie', CAST(police AS VARCHAR), mf_cin, ''
    FROM CRM_Maladie
    WHERE mf_cin IS NOT NULL
      AND LEN(mf_cin) IN (8,9,12)
      AND mf_cin NOT LIKE '%[^A-Za-z0-9]%'
      AND (
        mf_cin LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR mf_cin LIKE '0[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR mf_cin LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z][0-9][0-9][0-9][A-Z]'
      )

    UNION ALL

    SELECT 'parc01', police, cin, raison_sociale
    FROM parc01
    WHERE cin IS NOT NULL
      AND LEN(cin) IN (8,9,12)
      AND cin NOT LIKE '%[^A-Za-z0-9]%'
      AND (
        cin LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR cin LIKE '0[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
      )

    UNION ALL

    SELECT 'portdr01', police, cin, assure
    FROM portdr01
    WHERE cin IS NOT NULL
      AND LEN(cin) IN (8,9,12)
      AND cin NOT LIKE '%[^A-Za-z0-9]%'
      AND (
        cin LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR cin LIKE '0[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
      )

    UNION ALL

    SELECT 'CRM_RD_V2', police, cin, nom_assure
    FROM CRM_RD_V2
    WHERE cin IS NOT NULL
      AND LEN(cin) IN (8,9,12)
      AND cin NOT LIKE '%[^A-Za-z0-9]%'
      AND nature = 'PM'
      AND (
        cin LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
        OR cin LIKE '0[0-9][0-9][0-9][0-9][0-9][0-9][0-9][A-Z]'
      )
    """

    df_all = pd.read_sql(query, engine)

    # Dédupliquer par MF normalisé — inutile de vérifier 100x le même MF
    df_all["mf_norm_temp"] = df_all["mf_original"].str.strip().str.upper()
    df_unique = df_all.drop_duplicates(subset=["mf_norm_temp"]).copy()
    df_unique = df_unique.drop(columns=["mf_norm_temp"])

    total_avant_dedup = len(df_all)
    print(f"  MF dans toutes les tables : {total_avant_dedup:,}")
    print(f"  MF uniques a verifier     : {len(df_unique):,}")

    df = df_unique.rename(columns={"mf_original":"mf_original","nom":"prenom_nom"})

except Exception as e:
    print(f"  ❌ Erreur SQL Server : {str(e)[:100]}")
    print("\n  Configuration actuelle :")
    print(f"    • Serveur : {SERVER}")
    print(f"    • Base : {BASE}")
    print("\n  Vérifications requises :")
    print(f"    ✓ SQL Server est en ligne ?")
    print(f"    ✓ Authentification Windows activée ?")
    print(f"    ✓ Driver ODBC 17 for SQL Server installé ?")
    print(f"    ✓ Vous avez accès à cette base ?")
    print(f"\n  >> Relancez après correction")
    exit(1)

print(f"\n  {len(df)} MF a verifier sur le RNE")

# ── LANCEMENT SELENIUM ────────────────────────────────────────
driver = creer_driver()
print("\n  Connexion RNE...")
ok = se_connecter(driver)
if not ok:
    print("  Connexion echouee — verifier email/mot de passe")
    input("Entree..."); exit()
print(f"  Connexion OK")

print(f"\n{'='*65}")
print(f"  Verification en cours...")
print(f"{'='*65}")

resultats = []
for i, (_, row) in enumerate(df.iterrows(), 1):
    mf_brut = str(row.get("mf_original","") or "").strip()
    mf_norm, note = normaliser_mf(mf_brut)

    if mf_norm is None:
        statut, detail, raison = "INVALIDE", note, ""
    else:
        try:
            statut, detail, raison = verifier_mf(driver, mf_norm)
        except Exception as e:
            statut, detail, raison = "ERREUR", str(e)[:80], ""

    icone = ("OK" if statut=="TROUVE" else
             "KO" if statut=="NON_TROUVE" else
             "!!" if statut=="INVALIDE_FORMAT" else "??")

    if statut == "TROUVE" and raison:
        print(f"  [{i:>3}/{len(df)}] {mf_brut:<12} | {icone} -> {statut:<16} | {raison}")
    else:
        print(f"  [{i:>3}/{len(df)}] {mf_brut:<12} | {icone} -> {statut}")

    resultats.append({
        "source_table":        row.get("source_table",""),
        "police":              row.get("police",""),
        "nom_dataset":         row.get("prenom_nom",""),
        "mf_original":         mf_brut,
        "mf_normalise":        mf_norm or "N/A",
        "statut_rne":          statut,
        "raison_sociale_rne":  raison,
        "detail":              detail,
        "code_anomalie":       None if statut == "TROUVE" else "AN03",
        "libelle_anomalie": (
            "MF valide - present dans le RNE"    if statut == "TROUVE"          else
            "MF invalide - format non reconnu"    if statut == "INVALIDE_FORMAT" else
            "MF invalide - absent du RNE"         if statut == "NON_TROUVE"      else
            "MF a verifier manuellement"
        ),
        "statut_verification": (
            "VERIFIE_VALIDE"   if statut == "TROUVE"                            else
            "VERIFIE_INVALIDE" if statut in ("NON_TROUVE","INVALIDE_FORMAT")    else
            "NON_VERIFIE"
        ),
    })
    time.sleep(1)

df_res = pd.DataFrame(resultats)

# ── EXPORTS ───────────────────────────────────────────────────
excel_path = "C:/Users/DELL/Desktop/PFE M2/verification_mf_rne.xlsx"
df_res.to_excel(excel_path, index=False)

if engine is not None:
    try:
        df_res.to_sql("verification_mf_rne", engine,
                      if_exists="replace", index=False, chunksize=1000)
        print(f"\n  Export SQL Server : verification_mf_rne OK")
    except Exception as e:
        print(f"\n  Export SQL Server echoue : {e}")

# ── RÉSUMÉ ────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  RESULTATS — {len(df_res)} MF verifies")
print(f"{'='*65}")
for s, n in df_res["statut_rne"].value_counts().items():
    print(f"  {s:<22}: {n:>5}  ({n/len(df_res)*100:.1f}%)")

trouves = df_res[df_res.statut_rne == "TROUVE"]
if len(trouves) > 0:
    print(f"\n  MF TROUVES DANS LE RNE ({len(trouves)}) :")
    print(f"  {'-'*55}")
    for _, r in trouves.iterrows():
        print(f"  {r['mf_original']:<12} [{r['source_table']:<20}] {r['raison_sociale_rne']}")

non_trouves = df_res[df_res.statut_rne.isin(["NON_TROUVE","INVALIDE_FORMAT"])]
print(f"\n  MF ABSENTS / INVALIDES ({len(non_trouves)}) -> code AN03")

print(f"\n{'='*65}")
print(f"  Excel : {excel_path}")
print(f"{'='*65}")
input("\nAppuie sur Entree pour fermer...")
