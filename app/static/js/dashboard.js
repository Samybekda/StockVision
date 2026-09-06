/**
 * StockVision — Initialisation et rendu dynamique des graphiques Chart.js
 */

document.addEventListener("DOMContentLoaded", function () {
  const evolutionCtx = document.getElementById("evolutionChart");
  const categoryCtx = document.getElementById("categoryChart");
  const topProductsCtx = document.getElementById("topProductsChart");

  // Ne s'exécute que sur la page contenant les canvas
  if (!evolutionCtx || !categoryCtx || !topProductsCtx) {
    return;
  }

  fetch("/api/chart-data")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Erreur réseau lors de la récupération des données graphiques");
      }
      return response.json();
    })
    .then((data) => {
      renderEvolutionChart(evolutionCtx, data.evolution);
      renderCategoryChart(categoryCtx, data.category_distribution);
      renderTopProductsChart(topProductsCtx, data.top_products);
    })
    .catch((error) => {
      console.error("Erreur chargement graphiques:", error);
    });
});

/**
 * 1. Graphique d'évolution chronologique des mouvements (Entrées vs Sorties)
 */
function renderEvolutionChart(ctx, evolutionData) {
  new Chart(ctx, {
    type: "line",
    data: {
      labels: evolutionData.labels,
      datasets: [
        {
          label: "Entrées (IN)",
          data: evolutionData.in_data,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 6,
        },
        {
          label: "Sorties (OUT)",
          data: evolutionData.out_data,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "top",
          labels: {
            usePointStyle: true,
            boxWidth: 8,
          },
        },
        tooltip: {
          padding: 10,
          boxPadding: 4,
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
          ticks: {
            maxTicksLimit: 10,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "#f1f5f9",
          },
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
}

/**
 * 2. Graphique en anneau : Répartition du stock par catégorie
 */
function renderCategoryChart(ctx, categoryData) {
  const colors = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#ec4899",
    "#14b8a6",
    "#f97316",
  ];

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: categoryData.labels,
      datasets: [
        {
          data: categoryData.data,
          backgroundColor: colors.slice(0, categoryData.labels.length),
          borderWidth: 2,
          borderColor: "#ffffff",
          hoverOffset: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            padding: 14,
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const label = context.label || "";
              const value = context.raw || 0;
              const total = context.chart._metasets[context.datasetIndex].total;
              const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
              return ` ${label}: ${value} unité(s) (${percentage}%)`;
            },
          },
        },
      },
      cutout: "68%",
    },
  });
}

/**
 * 3. Graphique en barres horizontales : Top 5 des produits les plus actifs
 */
function renderTopProductsChart(ctx, topData) {
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: topData.labels,
      datasets: [
        {
          label: "Nombre de mouvements",
          data: topData.counts,
          backgroundColor: "#6366f1",
          borderRadius: 6,
          maxBarThickness: 24,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return ` ${context.raw} transaction(s) enregistrée(s)`;
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            color: "#f1f5f9",
          },
          ticks: {
            precision: 0,
          },
        },
        y: {
          grid: {
            display: false,
          },
        },
      },
    },
  });
}
