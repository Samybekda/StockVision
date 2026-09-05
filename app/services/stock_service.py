"""Service métier pour la gestion des stocks, mouvements, alertes et analyses."""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from app import db
from app.models import Product, Category, StockMovement, get_utc_now


class ValidationError(Exception):
    """Exception levée en cas d'erreur de validation métier."""
    pass


class StockService:
    """Couche de service centralisant les opérations et règles métier."""

    @staticmethod
    def create_product(
        reference: str,
        name: str,
        category_id: int,
        current_quantity: int = 0,
        min_threshold: int = 5,
        unit_price: float = 0.0,
    ) -> Product:
        """Crée un nouveau produit avec vérification d'unicité et contraintes positives."""
        reference = (reference or "").strip().upper()
        name = (name or "").strip()

        if not reference:
            raise ValidationError("La référence du produit est obligatoire.")
        if not name:
            raise ValidationError("Le nom du produit est obligatoire.")

        # Vérification unicité référence
        existing = Product.query.filter_by(reference=reference).first()
        if existing:
            raise ValidationError(
                f"La référence '{reference}' existe déjà pour le produit '{existing.name}'."
            )

        # Vérification existence catégorie
        category = db.session.get(Category, category_id)
        if not category:
            raise ValidationError(f"La catégorie spécifiée (ID: {category_id}) n'existe pas.")

        if current_quantity < 0:
            raise ValidationError("La quantité initiale ne peut pas être négative.")
        if min_threshold < 0:
            raise ValidationError("Le seuil minimum ne peut pas être négatif.")
        if unit_price < 0:
            raise ValidationError("Le prix unitaire ne peut pas être négatif.")

        product = Product(
            reference=reference,
            name=name,
            category_id=category_id,
            current_quantity=current_quantity,
            min_threshold=min_threshold,
            unit_price=float(unit_price),
        )

        db.session.add(product)
        db.session.commit()
        return product

    @staticmethod
    def update_product(
        product_id: int,
        name: str,
        category_id: int,
        min_threshold: int,
        unit_price: float,
        reference: Optional[str] = None,
    ) -> Product:
        """Met à jour les caractéristiques d'un produit (hors quantité directe)."""
        product = db.session.get(Product, product_id)
        if not product:
            raise ValidationError("Produit introuvable.")

        name = (name or "").strip()
        if not name:
            raise ValidationError("Le nom du produit ne peut pas être vide.")

        category = db.session.get(Category, category_id)
        if not category:
            raise ValidationError("Catégorie introuvable.")

        if reference:
            reference = reference.strip().upper()
            existing = Product.query.filter(
                Product.reference == reference, Product.id != product_id
            ).first()
            if existing:
                raise ValidationError(f"La référence '{reference}' est déjà utilisée.")
            product.reference = reference

        if min_threshold < 0:
            raise ValidationError("Le seuil minimum ne peut pas être négatif.")
        if unit_price < 0:
            raise ValidationError("Le prix unitaire ne peut pas être négatif.")

        product.name = name
        product.category_id = category_id
        product.min_threshold = min_threshold
        product.unit_price = float(unit_price)

        db.session.commit()
        return product

    @staticmethod
    def delete_product(product_id: int) -> bool:
        """Supprime un produit et son historique associé."""
        product = db.session.get(Product, product_id)
        if not product:
            raise ValidationError("Produit introuvable.")

        db.session.delete(product)
        db.session.commit()
        return True

    @staticmethod
    def record_movement(
        product_id: int,
        movement_type: str,
        quantity: int,
        comment: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> StockMovement:
        """
        Enregistre un mouvement de stock (entrée ou sortie) et met à jour
        automatiquement la quantité disponible du produit.

        Validation :
        - Quantité strictement positive (> 0)
        - Produit existant
        - Si sortie : la quantité demandée ne doit pas dépasser le stock disponible.
        """
        product = db.session.get(Product, product_id)
        if not product:
            raise ValidationError("Produit introuvable.")

        movement_type = (movement_type or "").strip().upper()
        if movement_type not in ("IN", "OUT"):
            raise ValidationError("Type de mouvement invalide. Utilisez 'IN' (Entrée) ou 'OUT' (Sortie).")

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise ValidationError("La quantité doit être un nombre entier valide.")

        if quantity <= 0:
            raise ValidationError("La quantité du mouvement doit être strictement supérieure à 0.")

        # Règle de gestion critique : interdiction de stock négatif
        if movement_type == "OUT":
            if quantity > product.current_quantity:
                raise ValidationError(
                    f"Stock insuffisant : vous tentez de sortir {quantity} unité(s) "
                    f"alors qu'il n'en reste que {product.current_quantity} en stock."
                )
            product.current_quantity -= quantity
        else:  # IN
            product.current_quantity += quantity

        if date is None:
            date = get_utc_now()
        elif date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        movement = StockMovement(
            product_id=product.id,
            movement_type=movement_type,
            quantity=quantity,
            comment=(comment or "").strip(),
            date=date,
        )

        db.session.add(movement)
        db.session.commit()
        return movement

    @staticmethod
    def calculate_consumption_trend(
        product_id: int, reference_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcule l'indicateur de tendance de consommation pour un produit.

        Logique statistique :
        - Période récente (30 derniers jours) : [T - 30j, T]
        - Période précédente (30 jours antérieurs) : [T - 60j, T - 30j[
        - Somme des sorties (OUT) sur chaque période.
        - Comparaison :
            * sorties_récentes > sorties_précédentes -> 'Hausse' (↑)
            * sorties_récentes < sorties_précédentes -> 'Baisse' (↓)
            * sorties_récentes == sorties_précédentes -> 'Stable' (→)
        """
        product = db.session.get(Product, product_id)
        if not product:
            raise ValidationError("Produit introuvable.")

        if reference_date is None:
            reference_date = get_utc_now()
        elif reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        t_current = reference_date
        t_30 = t_current - timedelta(days=30)
        t_60 = t_current - timedelta(days=60)

        # Sorties période récente (derniers 30 jours)
        recent_exits_query = db.session.query(
            func.coalesce(func.sum(StockMovement.quantity), 0)
        ).filter(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "OUT",
            StockMovement.date >= t_30,
            StockMovement.date <= t_current,
        ).scalar()
        recent_exits = int(recent_exits_query or 0)

        # Sorties période précédente (J-60 à J-30)
        previous_exits_query = db.session.query(
            func.coalesce(func.sum(StockMovement.quantity), 0)
        ).filter(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "OUT",
            StockMovement.date >= t_60,
            StockMovement.date < t_30,
        ).scalar()
        previous_exits = int(previous_exits_query or 0)

        delta = recent_exits - previous_exits

        if recent_exits > previous_exits:
            trend = "Hausse"
            label = "En hausse"
            icon = "bi-arrow-up-right"
            badge_class = "badge-trend-up"
            explanation = (
                f"+{delta} unité(s) sorties par rapport aux 30 jours précédents."
            )
        elif recent_exits < previous_exits:
            trend = "Baisse"
            label = "En baisse"
            icon = "bi-arrow-down-right"
            badge_class = "badge-trend-down"
            explanation = (
                f"{delta} unité(s) sorties par rapport aux 30 jours précédents."
            )
        else:
            trend = "Stable"
            label = "Stable"
            icon = "bi-arrow-right"
            badge_class = "badge-trend-stable"
            explanation = (
                "Consommation identique ou nulle sur les deux périodes comparées."
            )

        return {
            "product_id": product_id,
            "product_name": product.name,
            "product_reference": product.reference,
            "trend": trend,
            "label": label,
            "icon": icon,
            "badge_class": badge_class,
            "recent_exits": recent_exits,
            "previous_exits": previous_exits,
            "delta": delta,
            "explanation": explanation,
        }

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Agrège les métriques clés pour la page dashboard."""
        total_products = Product.query.count()

        # Quantité totale en stock (somme des unités actuelles)
        total_quantity = db.session.query(
            func.coalesce(func.sum(Product.current_quantity), 0)
        ).scalar()
        total_quantity = int(total_quantity)

        # Valeur totale du stock = sum(current_quantity * unit_price)
        total_value = db.session.query(
            func.coalesce(func.sum(Product.current_quantity * Product.unit_price), 0.0)
        ).scalar()
        total_value = round(float(total_value), 2)

        # Nombre de produits en alerte stock faible
        low_stock_count = Product.query.filter(
            Product.current_quantity < Product.min_threshold
        ).count()

        # Mouvements du mois en cours
        now = get_utc_now()
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        movements_month_count = StockMovement.query.filter(
            StockMovement.date >= start_of_month
        ).count()

        return {
            "total_products": total_products,
            "total_quantity": total_quantity,
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "movements_month_count": movements_month_count,
        }

    @staticmethod
    def get_chart_data() -> Dict[str, Any]:
        """
        Fournit les séries de données structurées pour les 3 graphiques Chart.js :
        1. Évolution chronologique des mouvements (30 derniers jours)
        2. Répartition du stock par catégorie
        3. Top 5 des produits les plus actifs en mouvements
        """
        now = get_utc_now()
        t_30 = now - timedelta(days=29)

        # 1. Évolution chronologique (30 derniers jours)
        daily_labels = []
        daily_in = []
        daily_out = []

        # Génération des 30 jours
        for i in range(30):
            day_date = (t_30 + timedelta(days=i)).date()
            day_str = day_date.strftime("%d/%m")
            daily_labels.append(day_str)

            # Somme IN du jour
            start_dt = datetime.combine(day_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_dt = datetime.combine(day_date, datetime.max.time()).replace(tzinfo=timezone.utc)

            in_qty = db.session.query(func.coalesce(func.sum(StockMovement.quantity), 0)).filter(
                StockMovement.movement_type == "IN",
                StockMovement.date >= start_dt,
                StockMovement.date <= end_dt,
            ).scalar()

            out_qty = db.session.query(func.coalesce(func.sum(StockMovement.quantity), 0)).filter(
                StockMovement.movement_type == "OUT",
                StockMovement.date >= start_dt,
                StockMovement.date <= end_dt,
            ).scalar()

            daily_in.append(int(in_qty))
            daily_out.append(int(out_qty))

        # 2. Stock par catégorie
        categories = Category.query.all()
        cat_labels = []
        cat_stock = []
        cat_values = []
        for cat in categories:
            total_qty = sum(p.current_quantity for p in cat.products)
            total_val = sum(p.stock_value for p in cat.products)
            if total_qty > 0 or cat.products.count() > 0:
                cat_labels.append(cat.name)
                cat_stock.append(total_qty)
                cat_values.append(round(total_val, 2))

        # 3. Top 5 produits avec le plus de mouvements (total des transactions)
        top_movements_query = (
            db.session.query(
                Product.name,
                func.count(StockMovement.id).label("mvt_count"),
                func.sum(StockMovement.quantity).label("total_volume"),
            )
            .join(StockMovement, Product.id == StockMovement.product_id)
            .group_by(Product.id, Product.name)
            .order_by(func.count(StockMovement.id).desc())
            .limit(5)
            .all()
        )

        top_labels = [item[0] for item in top_movements_query]
        top_counts = [int(item[1]) for item in top_movements_query]

        return {
            "evolution": {
                "labels": daily_labels,
                "in_data": daily_in,
                "out_data": daily_out,
            },
            "category_distribution": {
                "labels": cat_labels,
                "data": cat_stock,
                "values": cat_values,
            },
            "top_products": {
                "labels": top_labels,
                "counts": top_counts,
            },
        }

    @staticmethod
    def import_products_from_csv(file_data) -> Dict[str, Any]:
        """
        Importe ou met à jour des produits à partir d'un flux ou texte CSV.

        Règles de gestion :
        - Détection automatique du séparateur (virgule ',' ou point-virgule ';').
        - Décodage sécurisé UTF-8 (avec ou sans BOM Excel) et repli latin-1.
        - Colonnes obligatoires : reference, name, category, current_quantity, min_threshold.
        - Colonne optionnelle : unit_price (défaut: 0.0 si absente ou vide).
        - Création automatique des catégories inexistantes.
        - Upsert : si la référence existe déjà, le produit est mis à jour ; sinon, il est créé.
        - Détection et collecte des erreurs ligne par ligne pour ne pas bloquer l'import des lignes valides.
        - Validation des types (quantités et seuils entiers >= 0, prix flottant >= 0).
        - Sauvegarde transactionnelle dans la base SQLite.
        """
        if not file_data:
            raise ValidationError("Le fichier CSV fourni est vide.")

        # Extraction du texte selon le type de données reçu (bytes, fichier ou chaîne)
        if isinstance(file_data, bytes):
            try:
                text_content = file_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                text_content = file_data.decode("latin-1")
        elif hasattr(file_data, "read"):
            raw = file_data.read()
            if isinstance(raw, bytes):
                try:
                    text_content = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text_content = raw.decode("latin-1")
            else:
                text_content = str(raw)
        else:
            text_content = str(file_data)

        # Filtrage des lignes vides
        lines = [line for line in text_content.splitlines() if line.strip()]
        if not lines:
            raise ValidationError("Le fichier CSV ne contient aucune donnée.")

        # Détection du séparateur (virgule ou point-virgule)
        header_line = lines[0]
        delimiter = ";" if header_line.count(";") > header_line.count(",") else ","

        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValidationError("Le fichier CSV ne contient pas d'en-tête.")

        # Normalisation des noms de colonnes (minuscules, sans espaces superflus)
        headers = [h.strip().lower() for h in raw_headers if h is not None]
        header_map = {name: idx for idx, name in enumerate(headers)}

        required_cols = {"reference", "name", "category", "current_quantity", "min_threshold"}
        missing_cols = required_cols - set(headers)
        if missing_cols:
            raise ValidationError(
                f"Colonnes obligatoires manquantes dans le CSV : {', '.join(sorted(missing_cols))}. "
                "Colonnes attendues : reference, name, category, current_quantity, min_threshold, unit_price"
            )

        added_count = 0
        updated_count = 0
        errors = []

        # Traitement ligne par ligne (ligne 1 = en-têtes, les données commencent à la ligne 2)
        for line_num, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue  # Ignorer les lignes totalement vides

            def get_col(col_name: str) -> str:
                idx = header_map.get(col_name)
                if idx is not None and idx < len(row):
                    return row[idx].strip()
                return ""

            ref = get_col("reference").upper()
            name = get_col("name")
            cat_name = get_col("category")
            qty_str = get_col("current_quantity")
            threshold_str = get_col("min_threshold")
            price_str = get_col("unit_price")

            # 1. Validation de la référence
            if not ref:
                errors.append({
                    "line": line_num,
                    "reference": "—",
                    "message": "La référence du produit est manquante ou vide.",
                })
                continue

            # 2. Validation du nom
            if not name:
                errors.append({
                    "line": line_num,
                    "reference": ref,
                    "message": "Le nom du produit est manquant ou vide.",
                })
                continue

            # 3. Validation de la catégorie
            if not cat_name:
                errors.append({
                    "line": line_num,
                    "reference": ref,
                    "message": "La catégorie est manquante ou vide.",
                })
                continue

            # 4. Validation de la quantité actuelle (entier >= 0)
            try:
                current_qty = int(qty_str)
                if current_qty < 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append({
                    "line": line_num,
                    "reference": ref,
                    "message": f"Quantité invalide ('{qty_str}'). Un entier positif ou nul est attendu.",
                })
                continue

            # 5. Validation du seuil minimum (entier >= 0)
            try:
                min_threshold = int(threshold_str)
                if min_threshold < 0:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append({
                    "line": line_num,
                    "reference": ref,
                    "message": f"Seuil minimum invalide ('{threshold_str}'). Un entier positif ou nul est attendu.",
                })
                continue

            # 6. Validation du prix unitaire (optionnel, float >= 0)
            unit_price = 0.0
            if price_str:
                try:
                    # Tolérance de la virgule comme séparateur décimal (ex: 12,50 -> 12.50)
                    unit_price = float(price_str.replace(",", "."))
                    if unit_price < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    errors.append({
                        "line": line_num,
                        "reference": ref,
                        "message": f"Prix unitaire invalide ('{price_str}'). Un nombre positif ou nul est attendu.",
                    })
                    continue

            # Résolution ou création automatique de la catégorie
            category = Category.query.filter(
                func.lower(Category.name) == cat_name.lower()
            ).first()
            if not category:
                category = Category(
                    name=cat_name,
                    description=f"Catégorie créée automatiquement lors de l'import CSV",
                )
                db.session.add(category)
                db.session.flush()  # Obtention immédiate de l'ID généré

            # Recherche d'un produit existant pour mise à jour (Upsert)
            existing_product = Product.query.filter_by(reference=ref).first()
            if existing_product:
                existing_product.name = name
                existing_product.category_id = category.id
                existing_product.current_quantity = current_qty
                existing_product.min_threshold = min_threshold
                existing_product.unit_price = unit_price
                updated_count += 1
            else:
                new_product = Product(
                    reference=ref,
                    name=name,
                    category_id=category.id,
                    current_quantity=current_qty,
                    min_threshold=min_threshold,
                    unit_price=unit_price,
                )
                db.session.add(new_product)
                added_count += 1

        # Validation transactionnelle dans SQLite
        db.session.commit()

        return {
            "success": True,
            "added": added_count,
            "updated": updated_count,
            "errors": errors,
            "total_processed": added_count + updated_count + len(errors),
        }

