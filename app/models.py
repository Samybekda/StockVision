from datetime import datetime, timezone
from sqlalchemy import CheckConstraint
from app import db


def get_utc_now():
    """Renvoie la date et l'heure actuelles en UTC."""
    return datetime.now(timezone.utc)


class Category(db.Model):
    """Modèle représentant une catégorie de produits."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    products = db.relationship(
        "Product", backref="category", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "products_count": self.products.count(),
        }


class Product(db.Model):
    """Modèle représentant un produit en stock."""
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("current_quantity >= 0", name="check_positive_stock"),
        CheckConstraint("min_threshold >= 0", name="check_positive_threshold"),
        CheckConstraint("unit_price >= 0", name="check_positive_price"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    current_quantity = db.Column(db.Integer, nullable=False, default=0)
    min_threshold = db.Column(db.Integer, nullable=False, default=5)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=get_utc_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now
    )

    movements = db.relationship(
        "StockMovement",
        backref="product",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="desc(StockMovement.date)",
    )

    @property
    def is_low_stock(self) -> bool:
        """Retourne True si la quantité actuelle est strictement inférieure au seuil minimum."""
        return self.current_quantity < self.min_threshold

    @property
    def stock_value(self) -> float:
        """Valeur monétaire totale du stock pour ce produit."""
        return round(self.current_quantity * self.unit_price, 2)

    @property
    def deficit(self) -> int:
        """Quantité manquante pour atteindre le seuil minimum."""
        return max(0, self.min_threshold - self.current_quantity)

    def __repr__(self):
        return f"<Product {self.reference} - {self.name} ({self.current_quantity})>"

    def to_dict(self):
        return {
            "id": self.id,
            "reference": self.reference,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "current_quantity": self.current_quantity,
            "min_threshold": self.min_threshold,
            "unit_price": self.unit_price,
            "is_low_stock": self.is_low_stock,
            "stock_value": self.stock_value,
            "deficit": self.deficit,
        }


class StockMovement(db.Model):
    """Modèle représentant une entrée ou sortie de stock."""
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_positive_quantity"),
        CheckConstraint("movement_type IN ('IN', 'OUT')", name="check_valid_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    movement_type = db.Column(db.String(10), nullable=False)  # 'IN' ou 'OUT'
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=get_utc_now, index=True)
    comment = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<StockMovement {self.movement_type} {self.quantity} for Product #{self.product_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_reference": self.product.reference if self.product else "",
            "product_name": self.product.name if self.product else "",
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "date": self.date.strftime("%Y-%m-%d %H:%M"),
            "comment": self.comment or "",
        }
