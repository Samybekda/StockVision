"""Script d'initialisation et de peuplement de la base de données avec des données de démonstration réalistes."""
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import Category, Product, StockMovement


def seed_database():
    app = create_app("development")

    with app.app_context():
        print("Réinitialisation de la base de données SQLite...")
        db.drop_all()
        db.create_all()

        now = datetime.now(timezone.utc)

        # 1. Catégories
        categories = {
            "ordinateurs": Category(
                name="Ordinateurs & Portables",
                description="PC portables, stations de travail et mini-PC professionnels",
            ),
            "peripheriques": Category(
                name="Périphériques & Affichage",
                description="Écrans, claviers ergonomiques, souris et casques audio",
            ),
            "reseau": Category(
                name="Réseaux & Connectique",
                description="Switchs gigabit, routeurs Wi-Fi, câbles RJ45 et adaptateurs USB-C",
            ),
            "stockage": Category(
                name="Stockage & Composants",
                description="Disques SSD NVMe, disques durs externes et barrettes RAM DDR5",
            ),
        }

        for cat in categories.values():
            db.session.add(cat)
        db.session.commit()

        # 2. Produits (mix de stocks sains et stocks faibles)
        products_data = [
            # Ordinateurs
            {
                "reference": "PC-DELL-LAT",
                "name": "Dell Latitude 5540 - 15.6'' Core i7 16Go 512Go SSD",
                "category": categories["ordinateurs"],
                "current_quantity": 18,
                "min_threshold": 5,
                "unit_price": 949.00,
            },
            {
                "reference": "PC-THK-X1C",
                "name": "Lenovo ThinkPad X1 Carbon Gen 11 - 14'' Core i7 32Go",
                "category": categories["ordinateurs"],
                "current_quantity": 2,  # ALERTE (seuil 5)
                "min_threshold": 5,
                "unit_price": 1450.00,
            },
            {
                "reference": "PC-MAC-M3P",
                "name": "Apple MacBook Pro 14'' M3 Pro 18Go 512Go",
                "category": categories["ordinateurs"],
                "current_quantity": 4,  # ALERTE (seuil 6)
                "min_threshold": 6,
                "unit_price": 1899.00,
            },
            # Périphériques
            {
                "reference": "ECR-DEL-27",
                "name": "Écran Dell UltraSharp 27'' 4K USB-C U2723QE",
                "category": categories["peripheriques"],
                "current_quantity": 22,
                "min_threshold": 8,
                "unit_price": 469.00,
            },
            {
                "reference": "CLV-LOG-MXM",
                "name": "Clavier sans fil Logitech MX Keys S Rétroéclairé",
                "category": categories["peripheriques"],
                "current_quantity": 3,  # ALERTE (seuil 10)
                "min_threshold": 10,
                "unit_price": 89.90,
            },
            {
                "reference": "SOU-LOG-MX3",
                "name": "Souris sans fil ergonomique Logitech MX Master 3S",
                "category": categories["peripheriques"],
                "current_quantity": 15,
                "min_threshold": 8,
                "unit_price": 79.90,
            },
            {
                "reference": "CAS-JAB-EV2",
                "name": "Casque Jabra Evolve2 65 Bluetooth avec micro réduction de bruit",
                "category": categories["peripheriques"],
                "current_quantity": 0,  # RUPTURE TOTALE (seuil 5)
                "min_threshold": 5,
                "unit_price": 149.00,
            },
            # Réseaux
            {
                "reference": "SWI-CIS-24P",
                "name": "Switch Cisco Catalyst 1000 24 Ports PoE+",
                "category": categories["reseau"],
                "current_quantity": 8,
                "min_threshold": 3,
                "unit_price": 540.00,
            },
            {
                "reference": "CAB-ETH-CAT6",
                "name": "Bobine Câble Ethernet RJ45 Cat6 UTP 100m",
                "category": categories["reseau"],
                "current_quantity": 14,
                "min_threshold": 4,
                "unit_price": 38.50,
            },
            # Stockage
            {
                "reference": "SSD-SAM-990",
                "name": "SSD NVMe Samsung 990 PRO 2To PCIe 4.0 M.2",
                "category": categories["stockage"],
                "current_quantity": 25,
                "min_threshold": 10,
                "unit_price": 175.00,
            },
            {
                "reference": "HDD-WDC-4TB",
                "name": "Disque Dur Externe WD My Book 4To USB 3.0",
                "category": categories["stockage"],
                "current_quantity": 1,  # ALERTE (seuil 6)
                "min_threshold": 6,
                "unit_price": 105.00,
            },
        ]

        products_dict = {}
        for p_data in products_data:
            p = Product(
                reference=p_data["reference"],
                name=p_data["name"],
                category_id=p_data["category"].id,
                current_quantity=p_data["current_quantity"],
                min_threshold=p_data["min_threshold"],
                unit_price=p_data["unit_price"],
            )
            db.session.add(p)
            products_dict[p_data["reference"]] = p

        db.session.commit()

        # 3. Historique de Mouvements sur 60 jours
        # Permet de démontrer concrètement :
        # - Des produits en Hausse (ex: MX Master 3S : plus de sorties récentes)
        # - Des produits en Baisse (ex: Dell Latitude : sorties antérieures fortes, puis accalmie)
        # - Des produits Stables (ex: Switch Cisco : sorties constantes)
        movements = [
            # --- Historique pour Lenovo ThinkPad (Rupture approchante) ---
            # J-50 : Entrée initiale
            StockMovement(
                product_id=products_dict["PC-THK-X1C"].id,
                movement_type="IN",
                quantity=10,
                comment="Réception commande fournisseur Lenovo",
                date=now - timedelta(days=50),
            ),
            # J-40 : Sortie 2
            StockMovement(
                product_id=products_dict["PC-THK-X1C"].id,
                movement_type="OUT",
                quantity=2,
                comment="Équipement équipe R&D",
                date=now - timedelta(days=40),
            ),
            # J-20 : Sortie 3 (Hausse récente)
            StockMovement(
                product_id=products_dict["PC-THK-X1C"].id,
                movement_type="OUT",
                quantity=3,
                comment="Arrivée nouveaux stagiaires",
                date=now - timedelta(days=20),
            ),
            # J-5 : Sortie 3
            StockMovement(
                product_id=products_dict["PC-THK-X1C"].id,
                movement_type="OUT",
                quantity=3,
                comment="Déploiement pôle conseil",
                date=now - timedelta(days=5),
            ),

            # --- Historique pour Dell Latitude 5540 (Tendance Baisse) ---
            # J-55 : Entrée 30
            StockMovement(
                product_id=products_dict["PC-DELL-LAT"].id,
                movement_type="IN",
                quantity=30,
                comment="Livraison annuelle lot Dell",
                date=now - timedelta(days=55),
            ),
            # J-45 : Sortie 8 (Période antérieure forte)
            StockMovement(
                product_id=products_dict["PC-DELL-LAT"].id,
                movement_type="OUT",
                quantity=8,
                comment="Renouvellement parc commercial",
                date=now - timedelta(days=45),
            ),
            # J-35 : Sortie 4
            StockMovement(
                product_id=products_dict["PC-DELL-LAT"].id,
                movement_type="OUT",
                quantity=4,
                comment="Affectation consultants",
                date=now - timedelta(days=35),
            ),
            # Total antérieur = 12
            # J-12 : Sortie 2 (Période récente plus faible -> Baisse)
            StockMovement(
                product_id=products_dict["PC-DELL-LAT"].id,
                movement_type="OUT",
                quantity=2,
                comment="Remplacement machine défaillante",
                date=now - timedelta(days=12),
            ),

            # --- Historique pour Clavier MX Keys S (Tendance Hausse) ---
            # J-45 : Sortie 2
            StockMovement(
                product_id=products_dict["CLV-LOG-MXM"].id,
                movement_type="OUT",
                quantity=2,
                comment="Dotation bureautique",
                date=now - timedelta(days=45),
            ),
            # J-18 : Sortie 5 (Hausse)
            StockMovement(
                product_id=products_dict["CLV-LOG-MXM"].id,
                movement_type="OUT",
                quantity=5,
                comment="Demande groupée télétravail",
                date=now - timedelta(days=18),
            ),
            # J-3 : Sortie 4
            StockMovement(
                product_id=products_dict["CLV-LOG-MXM"].id,
                movement_type="OUT",
                quantity=4,
                comment="Installation nouvelle salle de réunion",
                date=now - timedelta(days=3),
            ),

            # --- Historique pour Switch Cisco (Tendance Stable) ---
            # J-42 : Sortie 2
            StockMovement(
                product_id=products_dict["SWI-CIS-24P"].id,
                movement_type="OUT",
                quantity=2,
                comment="Infrastructure baie serveur étage 1",
                date=now - timedelta(days=42),
            ),
            # J-15 : Sortie 2 (Exactement égal -> Stable)
            StockMovement(
                product_id=products_dict["SWI-CIS-24P"].id,
                movement_type="OUT",
                quantity=2,
                comment="Infrastructure baie serveur étage 2",
                date=now - timedelta(days=15),
            ),

            # --- Historique pour Écran Dell 27'' (Mouvements récents réguliers) ---
            StockMovement(
                product_id=products_dict["ECR-DEL-27"].id,
                movement_type="IN",
                quantity=25,
                comment="Réassort fournisseur Dell France",
                date=now - timedelta(days=28),
            ),
            StockMovement(
                product_id=products_dict["ECR-DEL-27"].id,
                movement_type="OUT",
                quantity=3,
                comment="Postes graphistes",
                date=now - timedelta(days=10),
            ),

            # --- Historique pour SSD Samsung 990 PRO ---
            StockMovement(
                product_id=products_dict["SSD-SAM-990"].id,
                movement_type="IN",
                quantity=30,
                comment="Réception lot composants",
                date=now - timedelta(days=14),
            ),
            StockMovement(
                product_id=products_dict["SSD-SAM-990"].id,
                movement_type="OUT",
                quantity=5,
                comment="Upgrade serveurs locaux",
                date=now - timedelta(days=2),
            ),
        ]

        for mvt in movements:
            db.session.add(mvt)

        db.session.commit()

        print("Données initialisées avec succès !")
        print(f"- {Category.query.count()} Catégories créées")
        print(f"- {Product.query.count()} Produits insérés")
        print(f"- {Product.query.filter(Product.current_quantity < Product.min_threshold).count()} Produits en stock faible (alertes actives)")
        print(f"- {StockMovement.query.count()} Mouvements de stock historisés")


if __name__ == "__main__":
    seed_database()
