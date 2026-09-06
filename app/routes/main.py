"""Routes principales : Dashboard, Alertes, Analyse de consommation, Import CSV et API graphiques."""
import os
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, send_file, current_app
from app.models import Product, StockMovement, Category
from app.services.stock_service import StockService, ValidationError

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    """Page d'accueil Dashboard avec KPIs, raccourcis et graphiques."""
    metrics = StockService.get_dashboard_metrics()
    
    # 6 mouvements les plus récents pour le flux d'activité
    recent_movements = (
        StockMovement.query.order_by(StockMovement.date.desc()).limit(6).all()
    )
    
    # Produits prioritaires en alerte (déficit le plus important)
    critical_products = [
        p for p in Product.query.filter(Product.current_quantity < Product.min_threshold).all()
    ]
    critical_products.sort(key=lambda p: p.deficit, reverse=True)

    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "dashboard.html",
        metrics=metrics,
        recent_movements=recent_movements,
        critical_products=critical_products[:5],
        categories=categories,
    )


@main_bp.route("/alerts")
def alerts():
    """Page dédiée affichant UNIQUEMENT les produits nécessitant une action (stock faible)."""
    low_stock_products = [
        p for p in Product.query.filter(Product.current_quantity < Product.min_threshold).all()
    ]
    # Tri par déficit décroissant (les plus urgents en premier)
    low_stock_products.sort(key=lambda p: p.deficit, reverse=True)
    
    # Calcul de la valeur totale à réapprovisionner pour atteindre le seuil
    reorder_cost = sum(p.deficit * p.unit_price for p in low_stock_products)

    return render_template(
        "alerts/index.html",
        products=low_stock_products,
        total_alerts=len(low_stock_products),
        reorder_cost=round(reorder_cost, 2),
    )


@main_bp.route("/analytics")
def analytics():
    """
    Page d'analyse statistique : Tendance de consommation par produit.
    Compare les sorties des 30 derniers jours avec les 30 jours précédents (J-60 à J-30).
    """
    products = Product.query.order_by(Product.name).all()
    trends = []
    hausse_count = 0
    baisse_count = 0
    stable_count = 0

    for product in products:
        trend_info = StockService.calculate_consumption_trend(product.id)
        trends.append(trend_info)
        if trend_info["trend"] == "Hausse":
            hausse_count += 1
        elif trend_info["trend"] == "Baisse":
            baisse_count += 1
        else:
            stable_count += 1

    return render_template(
        "analytics/index.html",
        trends=trends,
        hausse_count=hausse_count,
        baisse_count=baisse_count,
        stable_count=stable_count,
        total_analyzed=len(trends),
    )


@main_bp.route("/api/chart-data")
def chart_data():
    """Endpoint API JSON alimentant dynamiquement les 3 graphiques Chart.js."""
    data = StockService.get_chart_data()
    return jsonify(data)


@main_bp.route("/import-csv", methods=["GET", "POST"])
def import_csv():
    """Page et traitement de l'importation de produits par fichier CSV."""
    if request.method == "POST":
        if "file" not in request.files:
            flash("Aucun fichier n'a été transmis.", "danger")
            return redirect(url_for("main.import_csv"))

        file = request.files["file"]
        if not file or not file.filename:
            flash("Veuillez sélectionner un fichier CSV depuis votre ordinateur.", "warning")
            return redirect(url_for("main.import_csv"))

        if not file.filename.lower().endswith(".csv"):
            flash("Format de fichier non supporté. Veuillez importer un fichier avec l'extension .csv.", "danger")
            return redirect(url_for("main.import_csv"))

        try:
            result = StockService.import_products_from_csv(file)
            added = result["added"]
            updated = result["updated"]
            errors_count = len(result["errors"])

            if errors_count > 0:
                flash(
                    f"Import terminé avec des anomalies : {added} produit(s) ajouté(s), "
                    f"{updated} produit(s) mis à jour, {errors_count} ligne(s) ignorée(s).",
                    "warning",
                )
            else:
                flash(
                    f"Importation réussie : {added} produit(s) ajouté(s) et {updated} produit(s) mis à jour.",
                    "success",
                )

            return render_template("import_csv.html", result=result)

        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("import_csv.html", result=None)
        except Exception as e:
            flash(f"Erreur inattendue lors du traitement du fichier : {str(e)}", "danger")
            return render_template("import_csv.html", result=None)

    return render_template("import_csv.html", result=None)


@main_bp.route("/download-sample-csv")
def download_sample_csv():
    """Permet de télécharger le fichier modèle example_stock.csv pour tester l'import."""
    base_dir = os.path.abspath(os.path.join(current_app.root_path, ".."))
    sample_file_path = os.path.join(base_dir, "data", "example_stock.csv")
    if not os.path.exists(sample_file_path):
        flash("Fichier d'exemple introuvable.", "warning")
        return redirect(url_for("main.import_csv"))

    return send_file(
        sample_file_path,
        as_attachment=True,
        download_name="example_stock.csv",
        mimetype="text/csv",
    )

