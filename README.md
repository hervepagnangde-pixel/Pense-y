# Pense-y

Application Streamlit multi-agents consacrée à l'analyse du marché financier marocain.

## État du projet

- Module 1 : interface Streamlit initialisée
- Module 2 : connecteurs d'information à intégrer
- Module 3 : orchestrateur initialisé
- Module 4 : premier calcul financier intégré
- Module 5 : prévisualisation des alertes intégrée

## Installation

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

### Linux ou macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Sécurité

Créer localement un fichier `.env` à partir de `.env.example`.

Ne jamais publier :

- les clés API ;
- les mots de passe ;
- les jetons d'accès ;
- les données privées ;
- les fichiers `.env`.
