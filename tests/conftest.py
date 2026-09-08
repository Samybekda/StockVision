"""Fixtures de test pour pytest avec base SQLite en mémoire."""
import pytest
from app import create_app, db
from app.models import Category, Product


@pytest.fixture
def app():
    """Crée une instance de l'application configurée pour les tests avec base en mémoire."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Client de test Flask pour simuler des requêtes HTTP."""
    return app.test_client()


@pytest.fixture
def sample_category(app):
    """Catégorie de test de base."""
    category = Category(name="Informatique", description="Matériel informatique")
    db.session.add(category)
    db.session.commit()
    return category


@pytest.fixture
def sample_product(app, sample_category):
    """Produit de test initialisé avec un stock de 50 et un seuil de 10."""
    product = Product(
        reference="TEST-REF-01",
        name="Ordinateur Portable Test",
        category_id=sample_category.id,
        current_quantity=50,
        min_threshold=10,
        unit_price=800.0,
    )
    db.session.add(product)
    db.session.commit()
    return product
