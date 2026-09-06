"""Routes pour l'enregistrement et la consultation des mouvements de stock."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import StockMovement, Product
from app.services.stock_service import StockService, ValidationError

movements_bp = Blueprint("movements", __name__)


@movements_bp.route("/")
def list_movements():
    """Historique des mouvements de stock avec filtres par produit et type."""
    product_id = request.args.get("product_id", type=int)
    m_type = request.args.get("type", "").strip().upper()

    query = StockMovement.query

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)

    if m_type in ("IN", "OUT"):
        query = query.filter(StockMovement.movement_type == m_type)

    movements = query.order_by(StockMovement.date.desc()).limit(150).all()
    products = Product.query.order_by(Product.name).all()

    return render_template(
        "movements/index.html",
        movements=movements,
        products=products,
        selected_product_id=product_id,
        selected_type=m_type,
        total_count=len(movements),
    )


@movements_bp.route("/create", methods=["POST"])
def create_movement():
    """
    Enregistre un mouvement d'entrée ou de sortie avec validation stricte du stock disponible.
    """
    next_url = request.form.get("next") or request.referrer or url_for("movements.list_movements")

    try:
        product_id = request.form.get("product_id", type=int)
        movement_type = request.form.get("movement_type", "").strip().upper()
        comment = request.form.get("comment", "").strip()

        try:
            quantity = int(request.form.get("quantity", 0))
        except (ValueError, TypeError):
            raise ValidationError("La quantité doit être un nombre entier valide.")

        if not product_id:
            raise ValidationError("Veuillez sélectionner un produit.")

        movement = StockService.record_movement(
            product_id=product_id,
            movement_type=movement_type,
            quantity=quantity,
            comment=comment if comment else None,
        )

        type_label = "Entrée" if movement.movement_type == "IN" else "Sortie"
        flash(
            f"{type_label} de {movement.quantity} unité(s) enregistrée pour '{movement.product.name}'. "
            f"Nouveau stock : {movement.product.current_quantity}.",
            "success",
        )

    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erreur lors de l'enregistrement du mouvement : {str(e)}", "danger")

    return redirect(next_url)


@movements_bp.route("/api/product-stock/<int:product_id>")
def product_stock_api(product_id: int):
    """API légère renvoyant le stock actuel pour affichage dynamique dans les modales."""
    from app import db
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Produit introuvable"}), 404
    return jsonify({
        "id": product.id,
        "name": product.name,
        "reference": product.reference,
        "current_quantity": product.current_quantity,
        "min_threshold": product.min_threshold,
        "is_low_stock": product.is_low_stock,
    })
