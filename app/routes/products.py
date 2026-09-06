"""Routes pour la gestion des produits (CRUD, filtres, recherche)."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Product, Category
from app.services.stock_service import StockService, ValidationError

products_bp = Blueprint("products", __name__)


@products_bp.route("/")
def list_products():
    """Liste des produits avec recherche par nom/référence, filtre catégorie et filtre stock faible."""
    search_query = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", type=int)
    low_stock_filter = request.args.get("low_stock") in ("1", "true", "on")

    query = Product.query

    # 1. Recherche par nom ou référence
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            (Product.name.ilike(search_pattern)) | (Product.reference.ilike(search_pattern))
        )

    # 2. Filtre par catégorie
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # 3. Filtre stock faible
    if low_stock_filter:
        query = query.filter(Product.current_quantity < Product.min_threshold)

    products = query.order_by(Product.name).all()

    # Enrichissement avec l'indicateur de tendance de consommation
    product_items = []
    for p in products:
        trend = StockService.calculate_consumption_trend(p.id)
        product_items.append({"product": p, "trend": trend})

    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "products/index.html",
        product_items=product_items,
        categories=categories,
        search_query=search_query,
        selected_category_id=category_id,
        low_stock_filter=low_stock_filter,
        total_count=len(product_items),
    )


@products_bp.route("/create", methods=["POST"])
def create_product():
    """Création d'un nouveau produit avec validation des champs."""
    try:
        reference = request.form.get("reference", "").strip()
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id", type=int)
        
        try:
            current_quantity = int(request.form.get("current_quantity", 0))
        except (ValueError, TypeError):
            raise ValidationError("La quantité initiale doit être un nombre entier.")

        try:
            min_threshold = int(request.form.get("min_threshold", 5))
        except (ValueError, TypeError):
            raise ValidationError("Le seuil minimum doit être un nombre entier.")

        try:
            unit_price = float(request.form.get("unit_price", 0.0))
        except (ValueError, TypeError):
            raise ValidationError("Le prix unitaire doit être un nombre décimal valide.")

        if not category_id:
            raise ValidationError("Veuillez sélectionner une catégorie valide.")

        product = StockService.create_product(
            reference=reference,
            name=name,
            category_id=category_id,
            current_quantity=current_quantity,
            min_threshold=min_threshold,
            unit_price=unit_price,
        )
        flash(f"Produit '{product.name}' ({product.reference}) créé avec succès.", "success")

    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Une erreur inattendue est survenue : {str(e)}", "danger")

    return redirect(url_for("products.list_products"))


@products_bp.route("/<int:product_id>/edit", methods=["POST"])
def edit_product(product_id: int):
    """Modification des attributs d'un produit existant."""
    try:
        name = request.form.get("name", "").strip()
        reference = request.form.get("reference", "").strip()
        category_id = request.form.get("category_id", type=int)

        try:
            min_threshold = int(request.form.get("min_threshold", 5))
        except (ValueError, TypeError):
            raise ValidationError("Le seuil minimum doit être un nombre entier.")

        try:
            unit_price = float(request.form.get("unit_price", 0.0))
        except (ValueError, TypeError):
            raise ValidationError("Le prix unitaire doit être un nombre décimal.")

        if not category_id:
            raise ValidationError("Veuillez sélectionner une catégorie.")

        product = StockService.update_product(
            product_id=product_id,
            name=name,
            reference=reference if reference else None,
            category_id=category_id,
            min_threshold=min_threshold,
            unit_price=unit_price,
        )
        flash(f"Produit '{product.name}' mis à jour avec succès.", "success")

    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erreur lors de la modification : {str(e)}", "danger")

    return redirect(url_for("products.list_products"))


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id: int):
    """Suppression d'un produit et de son historique de mouvements."""
    try:
        StockService.delete_product(product_id)
        flash("Produit supprimé avec succès.", "success")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")

    return redirect(url_for("products.list_products"))
