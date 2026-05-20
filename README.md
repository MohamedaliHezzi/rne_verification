# RNE Verification — Selenium

Vérification automatisée des identifiants (MF) contre le Registre National des Entreprises (RNE) tunisien via Selenium.

## Structure du projet

```
rne_verification/
├── verification_rne_selenium.py  # Script principal
├── .env                          # Variables d'environnement (local uniquement)
├── .env.example                  # Modèle .env à copier
├── .gitignore                    # Fichiers à ignorer dans Git
├── requirements.txt              # Dépendances Python
└── README.md                     # Ce fichier
```

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/MohamedaliHezzi/rne_verification.git
cd rne_verification
```

### 2. Créer l'environnement Python (optionnel mais recommandé)

```bash
python -m venv venv
# Sur Windows
venv\Scripts\activate
# Sur macOS/Linux
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env
```

Éditer le fichier `.env` et remplir vos identifiants RNE :

```
RNE_EMAIL=votre_email@example.com
RNE_PASSWORD=votre_mot_de_passe
```

**⚠️ IMPORTANT** : Le fichier `.env` ne doit **JAMAIS** être commité sur GitHub (voir `.gitignore`).

## Utilisation

```bash
python verification_rne_selenium.py
```

Le script :
1. Se connecte au RNE Public
2. Charge les identifiants (MF) depuis SQL Server ou une liste locale
3. Vérifie chaque identifiant contre le RNE
4. Exporte les résultats en Excel et SQL Server

### Résultats

- **TROUVE** : MF valide, présent dans le RNE
- **NON_TROUVE** : MF absent du RNE (anomalie AN03)
- **INVALIDE_FORMAT** : Format non reconnu par le RNE
- **ERREUR** : Erreur lors de la vérification

## Configuration

Les variables d'environnement (fichier `.env`) :

| Variable | Description |
|----------|-------------|
| `RNE_EMAIL` | Email de connexion RNE Public |
| `RNE_PASSWORD` | Mot de passe RNE Public |

Les paramètres du script (lignes 23-30) :

| Variable | Description |
|----------|-------------|
| `SERVER` | Serveur SQL Server |
| `BASE` | Nom de la base de données |
| `TIMEOUT` | Délai d'attente Selenium (en secondes) |
| `RNE_URL` | URL du RNE Public |
| `LOGIN_URL` | URL de connexion RNE |

## Dépendances

- **selenium** : Automatisation du navigateur Chrome
- **pandas** : Manipulation des données
- **sqlalchemy** : Connexion à SQL Server
- **pyodbc** : Driver ODBC pour SQL Server
- **python-dotenv** : Chargement des variables d'environnement
- **webdriver-manager** : Gestion automatique du ChromeDriver
- **openpyxl** : Export en Excel

## Contribution

Les contributions sont bienvenues ! Pour proposer une modification :

1. Fork le dépôt
2. Créer une branche (`git checkout -b feature/ma-feature`)
3. Commit les changements (`git commit -m 'feat: description'`)
4. Pusher la branche (`git push origin feature/ma-feature`)
5. Ouvrir une Pull Request

## Licence

MIT License — voir le fichier LICENSE pour plus de détails.

## Auteur

Mohamed Ali Hezzi — [@MohamedaliHezzi](https://github.com/MohamedaliHezzi)

## Sécurité

**IMPORTANT** : Ne mettez **JAMAIS** vos credentials dans le code ou dans Git.
- Utilisez un fichier `.env` local (ignoré par Git)
- Copier le `.env.example` comme base
- Le `.gitignore` protège automatiquement votre `.env`
