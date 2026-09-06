/**
 * StockVision — Logique d'interface dynamique (modales, filtres, réapprovisionnement)
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Toggle du sidebar mobile
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("active");
    });
  }

  // 2. Gestion de l'affichage en direct du stock disponible lors du choix d'un produit dans la modale de mouvement
  const movementProductSelect = document.getElementById("movementProductSelect");
  const currentStockNotice = document.getElementById("currentStockNotice");
  const movementTypeSelect = document.getElementById("movementTypeSelect");

  if (movementProductSelect && currentStockNotice) {
    function updateStockNotice() {
      const selectedOption = movementProductSelect.options[movementProductSelect.selectedIndex];
      const stock = selectedOption.getAttribute("data-stock");
      const ref = selectedOption.getAttribute("data-ref");

      if (stock !== null) {
        currentStockNotice.innerHTML = `Stock actuellement disponible : <strong>${stock} unité(s)</strong> (Réf: ${ref})`;
        currentStockNotice.classList.remove("d-none");
      } else {
        currentStockNotice.classList.add("d-none");
      }
    }

    movementProductSelect.addEventListener("change", updateStockNotice);
    // Initialisation
    if (movementProductSelect.value) {
      updateStockNotice();
    }
  }

  // 3. Préremplissage de la modale de modification de produit
  const editProductModal = document.getElementById("editProductModal");
  if (editProductModal) {
    editProductModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      if (!button) return;

      const id = button.getAttribute("data-id");
      const ref = button.getAttribute("data-ref");
      const name = button.getAttribute("data-name");
      const catId = button.getAttribute("data-cat");
      const threshold = button.getAttribute("data-threshold");
      const price = button.getAttribute("data-price");

      const form = document.getElementById("editProductForm");
      form.action = `/products/${id}/edit`;

      document.getElementById("edit_product_id").value = id;
      document.getElementById("edit_reference").value = ref;
      document.getElementById("edit_name").value = name;
      document.getElementById("edit_category_id").value = catId;
      document.getElementById("edit_min_threshold").value = threshold;
      document.getElementById("edit_unit_price").value = price;
    });
  }

  // 4. Préremplissage de la modale de suppression de produit
  const deleteProductModal = document.getElementById("deleteProductModal");
  if (deleteProductModal) {
    deleteProductModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      if (!button) return;

      const id = button.getAttribute("data-id");
      const name = button.getAttribute("data-name");
      const ref = button.getAttribute("data-ref");

      const form = document.getElementById("deleteProductForm");
      form.action = `/products/${id}/delete`;

      document.getElementById("deleteProductName").textContent = `${name} (${ref})`;
    });
  }

  // 5. Préremplissage du mouvement rapide depuis les tableaux (ex: bouton Réapprovisionner)
  const quickMovementModal = document.getElementById("quickMovementModal");
  if (quickMovementModal) {
    quickMovementModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      if (!button) return;

      const productId = button.getAttribute("data-product-id");
      const movementType = button.getAttribute("data-type") || "IN";
      const suggestedQty = button.getAttribute("data-suggested-qty") || 1;

      if (productId && movementProductSelect) {
        movementProductSelect.value = productId;
        movementProductSelect.dispatchEvent(new Event("change"));
      }

      if (movementTypeSelect) {
        movementTypeSelect.value = movementType;
      }

      const qtyInput = document.getElementById("movementQuantityInput");
      if (qtyInput && suggestedQty) {
        qtyInput.value = suggestedQty;
      }
    });
  }
});
