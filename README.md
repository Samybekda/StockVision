# 📦 StockVision — Suivi & Analyse des Stocks

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)](https://www.sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-orange.svg)](https://www.chartjs.org/)
[![Tests](https://img.shields.io/badge/Tests-pytest%20(15%2F15%20passed)-brightgreen.svg)](https://pytest.org/)

**StockVision** est une application web légère, robuste et intuitive permettant de remplacer la gestion de stock manuelle sur papier par une solution numérique centralisée. Elle permet d'importer des catalogues depuis des fichiers CSV, de stocker les données de façon permanente dans une base SQLite, de gérer les entrées/sorties et d'anticiper les ruptures grâce à des alertes automatiques et une analyse statistique de la demande.

> **Projet personnel — Étudiant L3 MIAGE**  
> Conçu pour être simple, fini, lisible et facilement explicable lors d'un entretien de stage.

---

## 1. Présentation de StockVision

StockVision est une application web développée en Python/Flask destinée aux petites entreprises, commerces ou services internes souhaitant fiabiliser leur inventaire sans la lourdeur d'un ERP ou WMS complexe.

L'application prend en charge le cycle complet :
1. **Importation initiale ou périodique** via un fichier CSV.
2. **Stockage sécurisé et persistant** dans une base relationnelle SQLite avec SQLAlchemy.
3. **Mouvements de stock en direct** (entrées de réassort, sorties pour vente ou dotation).
4. **Surveillance proactive** avec détection automatique des niveaux critiques (stock faible).
5. **Aide à la décision** via un tableau de bord graphique et un indicateur statistique de tendance.

---

## 2. Problème Identifié

Lors de stages et de jobs étudiants, le constat est récurrent : de nombreuses structures effectuent encore leur suivi de stock sur **des fiches papier** ou des cahiers d'inventaire :
- **Risque élevé d'erreurs** : calculs manuels faux, fiches égarées, oublis de pointage.
- **Retards de réapprovisionnement** : la rupture est découverte au moment où le rayon est déjà vide.
- **Aucune traçabilité** : impossible de savoir quand, par qui et pourquoi un produit est sorti.
- **Perte de temps** : ressaisies manuelles chronophages et fastidieuses.

---

## 3. Solution Proposée

StockVision remplace ce fonctionnement manuel par un pipeline numérique simple :

```text
CSV (Données sources)
  ↓
Flask (Réception web & Contrôleur)
  ↓
Import Python (Parsing, Détection séparateur, Validation)
  ↓
SQLAlchemy (ORM & Intégrité relationnelle)
  ↓
SQLite (Stockage permanent sur disque)
  ↓
StockVision (Dashboard, Alertes, Flux & Mouvements)
```

1. **Numérisation facile** : un fichier CSV préparé sur tableur suffit pour charger tout le stock.
2. **Persistance garantie** : les données restent conservées dans SQLite même après arrêt de l'ordinateur.
3. **Zéro stock négatif** : contrôle strict au niveau service et base (interdiction mathématique de sortir plus d'unités qu'il n'en existe).
4. **Alertes visuelles immédiates** dès qu'une référence passe sous son seuil de sécurité.

---

## 4. Technologies Utilisées

Le choix technique privilégie la simplicité, la légèreté et la robustesse :

- **Backend** : Python 3.12+, Flask 3.1 (Application Factory, Blueprints).
- **Persistance & ORM** : SQLite 3 (base fichier légère), SQLAlchemy 2.0.
- **Frontend** : HTML5 sémantique, CSS3 moderne (palette navy/slate), JavaScript Vanilla (sans framework lourd).
- **Composants d'interface** : Bootstrap 5.3 & Bootstrap Icons (via CDN).
- **Graphiques** : Chart.js 4.4 (courbes de flux, anneau de catégories, top produits).
- **Tests automatisés** : pytest 9.1 (15 tests unitaires et d'intégration).

---

## 5. Fonctionnement de l'Import CSV

La fonctionnalité d'importation CSV suit un algorithme clair et tolérant :

1. **Détection automatique du séparateur** : l'application analyse l'en-tête pour accepter indifféremment la virgule (`,`) et le point-virgule (`;`).
2. **Encodage universel** : support transparent de l'UTF-8 et de l'UTF-8 avec BOM (format exporté par défaut par Microsoft Excel sous Windows).
3. **Vérification des colonnes obligatoires** : `reference`, `name`, `category`, `current_quantity`, `min_threshold` (la colonne `unit_price` est optionnelle, par défaut à `0.0`).
4. **Création automatique des catégories** : si une catégorie mentionnée dans le CSV n'existe pas encore en base, StockVision la crée automatiquement.
5. **Stratégie d'Upsert sans doublon** :
   - La **référence** constitue la clé logique unique du produit.
   - Si la référence **existe déjà** : les informations du produit (nom, catégorie, quantité, seuil, prix) sont mises à jour.
   - Si la référence **n'existe pas** : un nouveau produit est créé.
6. **Robustesse et isolation des erreurs** : si une ligne comporte une anomalie (ex: quantité négative), elle est isolée avec son numéro de ligne sans bloquer l'import des lignes valides.
7. **Compte-rendu détaillé** : affichage du nombre de produits créés, mis à jour et du tableau des lignes ignorées.

---

## 6. Exemple de Format CSV

Le fichier d'exemple pédagogique est disponible dans le projet sous [`data/example_stock.csv`](file:///c:/Users/MON%20PC/Documents/StockVision/data/example_stock.csv).

### Spécification des colonnes

| Colonne | Obligatoire ? | Type attendu | Exemple | Description |
| :--- | :---: | :---: | :--- | :--- |
| `reference` | **Oui** | Texte | `PC001` | Identifiant unique de la référence |
| `name` | **Oui** | Texte | `Dell Latitude 5540` | Désignation commerciale du produit |
| `category` | **Oui** | Texte | `Informatique` | Catégorie (créée si absente) |
| `current_quantity` | **Oui** | Entier $\ge 0$ | `15` | Quantité physique en stock |
| `min_threshold` | **Oui** | Entier $\ge 0$ | `5` | Seuil déclenchant l'alerte stock faible |
| `unit_price` | *Non* | Décimal $\ge 0.0$ | `899.00` | Prix unitaire en euros (défaut: `0.0`) |

### Extrait du fichier `data/example_stock.csv`

```csv
reference,name,category,current_quantity,min_threshold,unit_price
PC001,Ordinateur portable Dell Latitude 5540,Informatique,15,5,899.00
PC002,Lenovo ThinkPad X1 Carbon Gen 11,Informatique,3,5,1350.00
EC001,Écran 27 pouces 4K Dell UltraSharp,Affichage,12,6,450.00
CL001,Clavier ergonomique sans fil Logitech MX Keys,Accessoires,4,10,99.90
SO001,Souris optique bureautique filaire HP,Accessoires,40,15,14.50
SW001,Switch Ethernet Cisco 24 ports Gigabit PoE,Réseau,6,3,520.00
BU001,Chaise de bureau ergonomique réglable,Mobilier,5,2,240.00
```

> **Note :** Ce fichier est téléchargeable directement depuis l'interface web via le bouton **« Télécharger l'exemple (example_stock.csv) »** pour faciliter les démonstrations.

---

## 7. Architecture Générale du Projet

Le code respecte les principes de séparation des responsabilités (MVC + Service Layer) :

```text
StockVision/
├── app/
│   ├── __init__.py           # Application Factory Flask & Context Processors globaux
│   ├── models.py             # Modèles relationnels (Category, Product, StockMovement)
│   ├── routes/               # Contrôleurs HTTP (Blueprints Flask)
│   │   ├── main.py           # Dashboard, Import CSV, Alertes, Analyse & API JSON
│   │   ├── products.py       # CRUD Produits, Recherche & Filtres
│   │   └── movements.py      # Entrées / Sorties de stock
│   ├── services/             # Couche métier (Logique d'import, contrôles, calculs)
│   │   └── stock_service.py  # Fonctions métier atomiques et réutilisables
│   ├── static/
│   │   ├── css/style.css     # Design responsive moderne (Sidebar navy, badges, cartes)
│   │   └── js/
│   │       ├── dashboard.js  # Configuration et rendu des 3 graphiques Chart.js
│   │       └── main.js       # Gestion des modales et affichage du stock en direct
│   └── templates/            # Vues Jinja2 modulaires
│       ├── base.html         # Gabarit principal avec barre latérale et navigation
│       ├── dashboard.html    # 5 cartes KPI et graphiques opérationnels
│       ├── import_csv.html   # Page dédiée d'import CSV avec compte-rendu
│       ├── products/         # Catalogue et formulaires produits
│       ├── movements/        # Historique des transactions
│       ├── alerts/           # Page exclusive des stocks faibles avec déficit
│       └── analytics/        # Analyse statistique des tendances (J-30 vs J-60)
├── data/
│   └── example_stock.csv     # Fichier CSV de test (18 produits réalistes)
├── tests/
│   ├── conftest.py           # Configuration pytest et base SQLite en mémoire
│   └── test_stock.py         # 15 tests automatisés unitaires et d'intégration
├── config.py                 # Configuration Flask (Development, Testing)
├── seed.py                   # Script de peuplement initial réaliste (60j d'historique)
├── run.py                    # Point d'entrée pour démarrer l'application
├── requirements.txt          # Dépendances Python du projet
└── README.md                 # Documentation complète
```

---

## 8. Installation

### Prérequis
- Python 3.10 ou version ultérieure installée.

### 1. Cloner le projet
```bash
git clone https://github.com/Samybekda/StockVision.git
cd StockVision
```

### 2. Créer et activer l'environnement virtuel
**Sous Windows (PowerShell) :**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Sous Linux / macOS :**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

---

## 9. Lancement de l'Application

### Optionnel : Réinitialiser avec les données de démonstration
```bash
python seed.py
```
> *Ce script crée 4 catégories de base, 11 produits et un historique de 17 mouvements étalés sur 60 jours.*

### Démarrer le serveur web
```bash
python run.py
```
L'application démarre immédiatement sur : **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Tests Automatisés

La suite de tests automatisés avec `pytest` garantit le bon fonctionnement de toutes les briques logicielles :

```bash
pytest -v
```

### Détail des 15 tests exécutés :
- `test_create_product` : création conforme d'un produit et calcul de sa valorisation.
- `test_stock_entry` : incrémentation automatique de la quantité lors d'une entrée.
- `test_stock_exit` : décrémentation automatique de la quantité lors d'une sortie.
- `test_negative_stock_prevention` : blocage immédiat des sorties supérieures au stock disponible.
- `test_invalid_quantity_prevention` : rejet des quantités nulles ou négatives.
- `test_duplicate_reference_prevention` : rejet lors de la création d'un doublon de référence.
- `test_low_stock_detection` : calcul du statut `is_low_stock` et du déficit manquant.
- `test_consumption_trend_calculation` : validation mathématique des 3 états (Hausse, Baisse, Stable).
- `test_http_routes` : code HTTP 200 sur toutes les pages HTML et l'API JSON.
- `test_import_csv_valid` : import d'un CSV valide, vérification des créations et des catégories.
- `test_import_csv_update_existing` : mise à jour sans doublon d'une référence existante.
- `test_import_csv_semicolon_separator` : compatibilité avec le séparateur point-virgule (`;`).
- `test_import_csv_missing_mandatory_columns` : rejet des CSV incomplets avec message d'erreur clair.
- `test_import_csv_invalid_rows_handling` : gestion robuste des lignes erronées sans bloquer les lignes saines.
- `test_import_csv_http_flow` : téléversement réel via formulaire web multipart.

---

## 🎓 Points Clés pour l'Entretien de Stage (L3 MIAGE)

Pour présenter ce projet de manière convaincante devant un recruteur ou un jury :

1. **Le contexte métier avant la technique** :
   Expliquez que le projet est né d'un constat terrain en job étudiant (fiches papier d'inventaire, erreurs de comptage, ruptures découvertes trop tard). StockVision répond à ce besoin avec un outil simple mais robuste.
2. **Le choix de l'import CSV** :
   Le CSV est le format pivot par excellence. Les utilisateurs peuvent continuer à préparer leur liste sur Excel ou LibreOffice et l'intégrer en un clic dans StockVision.
3. **L'intégrité des données dans SQLite** :
   Mettez en avant le fait que la base SQLite ne permet aucun état incohérent : contraintes SQL `CHECK`, transactions atomiques et vérification métier dans `StockService` pour empêcher tout stock négatif.
4. **La séparation des responsabilités** :
   Les contrôleurs (`routes/`) ne contiennent pas de requêtes complexes ni d'algorithme d'importation : tout est encapsulé dans `StockService`, ce qui rend le code propre, maintenable et testable à 100%.
5. **L'analyse statistique de tendance** :
   Soulignez le pragmatisme de la solution : une comparaison de fenêtres glissantes ($J-30$ vs $J-60$) simple et déterministe plutôt qu'un modèle de machine learning inutilement opaque.
