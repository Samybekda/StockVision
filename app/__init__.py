from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config_by_name

db = SQLAlchemy()


def create_app(config_name="default"):
    """Application factory pour StockVision."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)

    # Enregistrement des Blueprints
    from app.routes.main import main_bp
    from app.routes.products import products_bp
    from app.routes.movements import movements_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(movements_bp, url_prefix="/movements")

    # Création des tables dans le contexte de l'application
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    # Context processor pour injecter les alertes et la liste des produits dans toutes les vues
    @app.context_processor
    def inject_global_metrics():
        try:
            from app.models import Product
            low_stock_count = Product.query.filter(
                Product.current_quantity < Product.min_threshold
            ).count()
            global_products = Product.query.order_by(Product.name).all()
        except Exception:
            low_stock_count = 0
            global_products = []
        return {
            "global_low_stock_count": low_stock_count,
            "global_products": global_products,
        }

    return app
