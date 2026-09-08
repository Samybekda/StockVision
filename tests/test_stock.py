"""Tests unitaires et d'intégration pour StockVision."""
import io
from datetime import datetime, timedelta, timezone
import pytest
from app import db
from app.models import Product, StockMovement, Category
from app.services.stock_service import StockService, ValidationError


def test_create_product(app, sample_category):
    """Vérifie la création d'un produit et le calcul de sa valeur en stock."""
    with app.app_context():
        product = StockService.create_product(
            reference="REF-MON-01",
            name="Écran 24 pouces",
            category_id=sample_category.id,
            current_quantity=20,
            min_threshold=5,
            unit_price=150.0,
        )

        assert product.id is not None
        assert product.reference == "REF-MON-01"
        assert product.name == "Écran 24 pouces"
        assert product.current_quantity == 20
        assert product.min_threshold == 5
        assert product.unit_price == 150.0
        assert product.stock_value == 3000.0
        assert product.is_low_stock is False


def test_stock_entry(app, sample_product):
    """Vérifie qu'une entrée de stock incrémente correctement la quantité."""
    with app.app_context():
        initial_stock = sample_product.current_quantity  # 50
        movement = StockService.record_movement(
            product_id=sample_product.id,
            movement_type="IN",
            quantity=15,
            comment="Livraison fournisseur",
        )

        product = db.session.get(Product, sample_product.id)
        assert movement.quantity == 15
        assert movement.movement_type == "IN"
        assert product.current_quantity == initial_stock + 15  # 65


def test_stock_exit(app, sample_product):
    """Vérifie qu'une sortie de stock décrémente correctement la quantité."""
    with app.app_context():
        initial_stock = sample_product.current_quantity  # 50
        movement = StockService.record_movement(
            product_id=sample_product.id,
            movement_type="OUT",
            quantity=10,
            comment="Sortie vente client",
        )

        product = db.session.get(Product, sample_product.id)
        assert movement.quantity == 10
        assert movement.movement_type == "OUT"
        assert product.current_quantity == initial_stock - 10  # 40


def test_negative_stock_prevention(app, sample_product):
    """Vérifie l'impossibilité d'effectuer une sortie supérieure au stock disponible."""
    with app.app_context():
        current_stock = sample_product.current_quantity  # 50

        # Tentative de sortie de 51 unités alors qu'il n'y en a que 50
        with pytest.raises(ValidationError) as exc_info:
            StockService.record_movement(
                product_id=sample_product.id,
                movement_type="OUT",
                quantity=51,
                comment="Tentative sortie excessive",
            )

        assert "Stock insuffisant" in str(exc_info.value)

        # Vérification que le stock n'a pas bougé
        product = db.session.get(Product, sample_product.id)
        assert product.current_quantity == current_stock


def test_invalid_quantity_prevention(app, sample_product):
    """Vérifie le rejet des quantités nulles ou négatives."""
    with app.app_context():
        with pytest.raises(ValidationError) as exc_0:
            StockService.record_movement(
                product_id=sample_product.id,
                movement_type="IN",
                quantity=0,
            )
        assert "strictement supérieure à 0" in str(exc_0.value)

        with pytest.raises(ValidationError) as exc_neg:
            StockService.record_movement(
                product_id=sample_product.id,
                movement_type="OUT",
                quantity=-5,
            )
        assert "strictement supérieure à 0" in str(exc_neg.value)


def test_duplicate_reference_prevention(app, sample_category, sample_product):
    """Vérifie le rejet lors de la création d'un produit avec une référence déjà existante."""
    with app.app_context():
        with pytest.raises(ValidationError) as exc_info:
            StockService.create_product(
                reference="TEST-REF-01",  # Même référence que sample_product
                name="Doublon produit",
                category_id=sample_category.id,
                current_quantity=5,
            )

        assert "existe déjà" in str(exc_info.value)


def test_low_stock_detection(app, sample_category):
    """Vérifie la détection automatique du statut stock faible (current_quantity < min_threshold)."""
    with app.app_context():
        # Produit en stock sain
        p_normal = StockService.create_product(
            reference="REF-HEALTHY",
            name="Produit Normal",
            category_id=sample_category.id,
            current_quantity=10,
            min_threshold=5,
        )
        assert p_normal.is_low_stock is False
        assert p_normal.deficit == 0

        # Produit en stock faible
        p_low = StockService.create_product(
            reference="REF-LOW",
            name="Produit Seuil Critique",
            category_id=sample_category.id,
            current_quantity=3,
            min_threshold=8,
        )
        assert p_low.is_low_stock is True
        assert p_low.deficit == 5  # 8 - 3 = 5 manquants

        # Sortie amenant sous le seuil
        StockService.record_movement(
            product_id=p_normal.id,
            movement_type="OUT",
            quantity=6,  # 10 - 6 = 4 < seuil 5
        )
        p_updated = db.session.get(Product, p_normal.id)
        assert p_updated.is_low_stock is True


def test_consumption_trend_calculation(app, sample_category):
    """
    Vérifie l'algorithme statistique d'analyse de tendance de consommation :
    - Hausse : sorties récentes (J-30..J) > sorties antérieures (J-60..J-30)
    - Baisse : sorties récentes < sorties antérieures
    - Stable : sorties récentes == sorties antérieures
    """
    with app.app_context():
        ref_date = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

        # 1. Produit en Hausse
        p_hausse = StockService.create_product(
            reference="TREND-UP",
            name="Produit en forte demande",
            category_id=sample_category.id,
            current_quantity=100,
        )
        # Antérieur (J-45) : 5 sorties
        db.session.add(
            StockMovement(
                product_id=p_hausse.id,
                movement_type="OUT",
                quantity=5,
                date=ref_date - timedelta(days=45),
            )
        )
        # Récent (J-10) : 15 sorties
        db.session.add(
            StockMovement(
                product_id=p_hausse.id,
                movement_type="OUT",
                quantity=15,
                date=ref_date - timedelta(days=10),
            )
        )

        # 2. Produit en Baisse
        p_baisse = StockService.create_product(
            reference="TREND-DOWN",
            name="Produit en ralentissement",
            category_id=sample_category.id,
            current_quantity=100,
        )
        # Antérieur (J-40) : 20 sorties
        db.session.add(
            StockMovement(
                product_id=p_baisse.id,
                movement_type="OUT",
                quantity=20,
                date=ref_date - timedelta(days=40),
            )
        )
        # Récent (J-15) : 4 sorties
        db.session.add(
            StockMovement(
                product_id=p_baisse.id,
                movement_type="OUT",
                quantity=4,
                date=ref_date - timedelta(days=15),
            )
        )

        # 3. Produit Stable
        p_stable = StockService.create_product(
            reference="TREND-STABLE",
            name="Produit régulier",
            category_id=sample_category.id,
            current_quantity=100,
        )
        # Antérieur (J-35) : 8 sorties
        db.session.add(
            StockMovement(
                product_id=p_stable.id,
                movement_type="OUT",
                quantity=8,
                date=ref_date - timedelta(days=35),
            )
        )
        # Récent (J-8) : 8 sorties
        db.session.add(
            StockMovement(
                product_id=p_stable.id,
                movement_type="OUT",
                quantity=8,
                date=ref_date - timedelta(days=8),
            )
        )

        db.session.commit()

        trend_up = StockService.calculate_consumption_trend(p_hausse.id, reference_date=ref_date)
        assert trend_up["trend"] == "Hausse"
        assert trend_up["recent_exits"] == 15
        assert trend_up["previous_exits"] == 5
        assert trend_up["delta"] == 10

        trend_down = StockService.calculate_consumption_trend(p_baisse.id, reference_date=ref_date)
        assert trend_down["trend"] == "Baisse"
        assert trend_down["recent_exits"] == 4
        assert trend_down["previous_exits"] == 20
        assert trend_down["delta"] == -16

        trend_stable = StockService.calculate_consumption_trend(p_stable.id, reference_date=ref_date)
        assert trend_stable["trend"] == "Stable"
        assert trend_stable["recent_exits"] == 8
        assert trend_stable["previous_exits"] == 8
        assert trend_stable["delta"] == 0


def test_http_routes(client, sample_product):
    """Vérifie que les principales routes HTML et l'API JSON répondent avec un statut 200."""
    res_dashboard = client.get("/")
    assert res_dashboard.status_code == 200
    assert b"StockVision" in res_dashboard.data

    res_products = client.get("/products/")
    assert res_products.status_code == 200
    assert b"TEST-REF-01" in res_products.data

    res_movements = client.get("/movements/")
    assert res_movements.status_code == 200

    res_alerts = client.get("/alerts")
    assert res_alerts.status_code == 200

    res_analytics = client.get("/analytics")
    assert res_analytics.status_code == 200

    res_chart_api = client.get("/api/chart-data")
    assert res_chart_api.status_code == 200
    data = res_chart_api.get_json()
    assert "evolution" in data
    assert "category_distribution" in data
    assert "top_products" in data

    res_import_page = client.get("/import-csv")
    assert res_import_page.status_code == 200
    assert b"Importer un CSV" in res_import_page.data


def test_import_csv_valid(app):
    """Vérifie l'importation d'un CSV valide avec création automatique de catégories."""
    csv_content = """reference,name,category,current_quantity,min_threshold,unit_price
PC001,Ordinateur portable,Informatique,15,5,750
CL001,Clavier ergonomique,Accessoires,8,10,45
SO001,Souris filaire,Accessoires,20,5,25
"""
    with app.app_context():
        result = StockService.import_products_from_csv(csv_content)

        assert result["success"] is True
        assert result["added"] == 3
        assert result["updated"] == 0
        assert len(result["errors"]) == 0

        # Vérification en base SQLite
        p1 = Product.query.filter_by(reference="PC001").first()
        assert p1 is not None
        assert p1.name == "Ordinateur portable"
        assert p1.category.name == "Informatique"
        assert p1.current_quantity == 15
        assert p1.min_threshold == 5
        assert p1.unit_price == 750.0

        p2 = Product.query.filter_by(reference="CL001").first()
        assert p2 is not None
        assert p2.current_quantity == 8
        assert p2.is_low_stock is True  # 8 < 10

        # Vérification de la création des catégories
        cat_info = Category.query.filter_by(name="Informatique").first()
        cat_acc = Category.query.filter_by(name="Accessoires").first()
        assert cat_info is not None
        assert cat_acc is not None


def test_import_csv_update_existing(app):
    """Vérifie que l'import d'une référence déjà existante met à jour le produit sans créer de doublon."""
    csv_initial = """reference,name,category,current_quantity,min_threshold,unit_price
PC001,Dell Latitude,Informatique,10,5,800.0
"""
    csv_update = """reference,name,category,current_quantity,min_threshold,unit_price
PC001,Dell Latitude 5540 Nouveau,Informatique Pro,25,8,850.0
"""
    with app.app_context():
        res1 = StockService.import_products_from_csv(csv_initial)
        assert res1["added"] == 1
        assert res1["updated"] == 0

        res2 = StockService.import_products_from_csv(csv_update)
        assert res2["added"] == 0
        assert res2["updated"] == 1
        assert len(res2["errors"]) == 0

        # Vérification qu'il n'y a pas de doublon (1 seul produit)
        products = Product.query.filter_by(reference="PC001").all()
        assert len(products) == 1

        updated_p = products[0]
        assert updated_p.name == "Dell Latitude 5540 Nouveau"
        assert updated_p.category.name == "Informatique Pro"
        assert updated_p.current_quantity == 25
        assert updated_p.min_threshold == 8
        assert updated_p.unit_price == 850.0


def test_import_csv_semicolon_separator(app):
    """Vérifie la compatibilité avec le délimiteur point-virgule ';' et les virgules décimales."""
    csv_content = (
        "reference;name;category;current_quantity;min_threshold;unit_price\n"
        "ECR01;Écran 27 pouces;Affichage;12;4;249,90\n"
    )
    with app.app_context():
        result = StockService.import_products_from_csv(csv_content)
        assert result["success"] is True
        assert result["added"] == 1

        p = Product.query.filter_by(reference="ECR01").first()
        assert p is not None
        assert p.current_quantity == 12
        assert p.unit_price == 249.90


def test_import_csv_missing_mandatory_columns(app):
    """Vérifie le rejet explicite d'un CSV dont les colonnes obligatoires sont absentes."""
    # Manque 'category' et 'min_threshold'
    csv_invalid = """reference,name,current_quantity,unit_price
PC001,Ordinateur portable,15,750
"""
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            StockService.import_products_from_csv(csv_invalid)

        assert "Colonnes obligatoires manquantes" in str(exc.value)
        assert "category" in str(exc.value)
        assert "min_threshold" in str(exc.value)


def test_import_csv_invalid_rows_handling(app):
    """
    Vérifie la robustesse face aux anomalies par ligne :
    les lignes valides sont importées, les lignes en erreur sont isolées et signalées.
    """
    csv_content = """reference,name,category,current_quantity,min_threshold,unit_price
VALID01,Produit Valide,Bureautique,10,5,15.0
,Produit Sans Ref,Bureautique,10,5,15.0
NEG01,Quantite Negative,Bureautique,-3,5,15.0
PRC01,Prix Invalide,Bureautique,10,5,abc
"""
    with app.app_context():
        result = StockService.import_products_from_csv(csv_content)

        assert result["success"] is True
        assert result["added"] == 1  # Seul VALID01 doit être inséré
        assert result["updated"] == 0
        assert len(result["errors"]) == 3  # 3 lignes erronées

        assert Product.query.filter_by(reference="VALID01").first() is not None
        assert Product.query.filter_by(reference="NEG01").first() is None
        assert Product.query.filter_by(reference="PRC01").first() is None

        # Vérification de la présence des numéros de ligne dans le rapport d'erreurs
        error_lines = [e["line"] for e in result["errors"]]
        assert 3 in error_lines  # Ligne sans ref
        assert 4 in error_lines  # Ligne quantité négative
        assert 5 in error_lines  # Ligne prix invalide


def test_import_csv_http_flow(client):
    """Vérifie la route web POST /import-csv et le téléchargement du fichier modèle."""
    # 1. Test upload d'un fichier CSV valide via HTTP
    csv_bytes = b"reference,name,category,current_quantity,min_threshold,unit_price\nHTTP01,Web Product,Web Cat,5,2,20.0\n"
    data = {
        "file": (io.BytesIO(csv_bytes), "catalogue.csv")
    }
    response = client.post("/import-csv", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    assert b"HTTP01" in response.data or b"Importation r" in response.data

    # 2. Test téléchargement du fichier modèle example_stock.csv
    res_download = client.get("/download-sample-csv")
    assert res_download.status_code == 200
    assert "text/csv" in res_download.content_type
    assert b"PC001" in res_download.data

