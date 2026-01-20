/**
 * Chart.js wrapper for analytics P/L charts.
 * Reads data from window.plChartLabels and window.plChartData.
 */

/**
 * Initialize or reinitialize the P/L chart from window variables.
 * Call this after setting window.plChartLabels and window.plChartData.
 */
function initPLChart() {
    const canvas = document.getElementById('plChart');
    if (!canvas || typeof Chart === 'undefined') return;

    // Destroy existing chart if it exists
    if (window.plChartInstance) {
        window.plChartInstance.destroy();
    }

    // Get data from window variables set by partial template
    const labels = window.plChartLabels;
    const data = window.plChartData;
    if (!labels || !data) return;

    const ctx = canvas.getContext('2d');
    window.plChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative P/L',
                data: data,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: { display: true, text: 'Date' }
                },
                y: {
                    display: true,
                    title: { display: true, text: 'P/L ($)' },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        }
                    }
                }
            }
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initPLChart);

// Reinitialize after HTMX settles content (ensures inline scripts have run)
document.body.addEventListener('htmx:afterSettle', function(event) {
    if (event.detail.target.id === 'analytics-content') {
        initPLChart();
    }
});
