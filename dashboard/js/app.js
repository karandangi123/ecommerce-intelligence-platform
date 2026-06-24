// Switch Tabs
function switchTab(tabName) {
    // Deactivate all sections & tabs
    document.querySelectorAll('.view-section').forEach(section => {
        section.classList.remove('active');
    });
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Activate the clicked section & nav tab
    document.getElementById(`${tabName}-section`).classList.add('active');
    
    // Find the matching nav list item
    const navItems = document.querySelectorAll('.nav-item');
    if (tabName === 'ceo') navItems[0].classList.add('active');
    if (tabName === 'ops') navItems[1].classList.add('active');
    if (tabName === 'marketing') navItems[2].classList.add('active');
    if (tabName === 'geo') navItems[3].classList.add('active');
}

// Format numbers
function formatBRL(value) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
}

function formatNum(value) {
    return new Intl.NumberFormat('en-US').format(value);
}

// Global Chart Options for Premium Look
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: { color: '#9ca3af', font: { family: 'Outfit', size: 12 } }
        }
    },
    scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af', font: { family: 'Outfit' } } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af', font: { family: 'Outfit' } } }
    }
};

// Initialize Dashboard Data
async function initDashboard() {
    try {
        // --- 1. LOAD DATA ---
        const [
            ceoData, 
            opsData, 
            marketingData, 
            rfmSummary, 
            cohortData, 
            rootCause, 
            geoRevenue, 
            categoryPerformance, 
            paymentTrends
        ] = await Promise.all([
            fetch('data/ceo_monthly.json').then(r => r.json()),
            fetch('data/ops_monthly.json').then(r => r.json()),
            fetch('data/marketing_monthly.json').then(r => r.json()),
            fetch('data/rfm_summary.json').then(r => r.json()),
            fetch('data/cohort_retention.json').then(r => r.json()),
            fetch('data/delivery_root_cause.json').then(r => r.json()),
            fetch('data/geo_revenue.json').then(r => r.json()),
            fetch('data/category_performance.json').then(r => r.json()),
            fetch('data/payment_trends.json').then(r => r.json())
        ]);

        // --- 2. RENDER CEO VIEW ---
        // Find index of August 2018 for calculations
        const activeIdx = ceoData.findIndex(d => d.order_month === '2018-08-01');
        const activeCeoMonth = activeIdx !== -1 ? ceoData[activeIdx] : ceoData[ceoData.length - 2];
        const prevCeoMonth = activeIdx > 0 ? ceoData[activeIdx - 1] : ceoData[ceoData.length - 3];
        
        // Calculate True LTM (Last 12 Months) rolling sum up to active month
        const ltmStartIdx = Math.max(0, activeIdx - 11);
        const ltmData = ceoData.slice(ltmStartIdx, activeIdx + 1);
        const ltmRevenue = ltmData.reduce((sum, d) => sum + d.total_revenue, 0);
        const ltmOrders = ltmData.reduce((sum, d) => sum + d.total_orders, 0);
        
        // Calculate Previous True LTM (Last 12 Months) rolling sum up to previous month
        const prevLtmStartIdx = Math.max(0, activeIdx - 12);
        const prevLtmData = ceoData.slice(prevLtmStartIdx, activeIdx);
        const prevLtmRevenue = prevLtmData.reduce((sum, d) => sum + d.total_revenue, 0);
        const prevLtmOrders = prevLtmData.reduce((sum, d) => sum + d.total_orders, 0);
        
        // Populate LTM Cards
        document.getElementById('ceo-ltm-revenue').innerText = formatBRL(ltmRevenue);
        document.getElementById('ceo-ltm-orders').innerText = formatNum(ltmOrders);
        
        const ltmRevenueGrowth = ((ltmRevenue - prevLtmRevenue) / prevLtmRevenue) * 100;
        const ltmOrdersGrowth = ((ltmOrders - prevLtmOrders) / prevLtmOrders) * 100;
        renderDeltaBadge('ceo-ltm-revenue-delta', ltmRevenueGrowth, '% MoM (LTM)');
        renderDeltaBadge('ceo-ltm-orders-delta', ltmOrdersGrowth, '% MoM (LTM)');
        
        // Populate Monthly Cards
        document.getElementById('ceo-monthly-revenue').innerText = formatBRL(activeCeoMonth.total_revenue);
        document.getElementById('ceo-monthly-orders').innerText = formatNum(activeCeoMonth.total_orders);
        renderDeltaBadge('ceo-monthly-revenue-delta', activeCeoMonth.mom_revenue_growth_pct, '% MoM');
        renderDeltaBadge('ceo-monthly-orders-delta', activeCeoMonth.mom_orders_growth_pct, '% MoM');
        
        // Populate AOV & OTD
        document.getElementById('ceo-aov').innerText = formatBRL(activeCeoMonth.avg_order_value);
        const aovGrowth = ((activeCeoMonth.avg_order_value - prevCeoMonth.avg_order_value) / prevCeoMonth.avg_order_value) * 100;
        renderDeltaBadge('ceo-aov-delta', aovGrowth, '% MoM');
        
        const activeOpsMonth = opsData.find(d => d.order_month === '2018-08-01') || opsData[opsData.length - 2];
        const prevOpsMonth = opsData.find(d => d.order_month === '2018-07-01') || opsData[opsData.length - 3];
        
        document.getElementById('ceo-otd').innerText = `${activeOpsMonth.otd_pct}%`;
        const otdGrowth = activeOpsMonth.otd_pct - prevOpsMonth.otd_pct;
        renderDeltaBadge('ceo-otd-delta', otdGrowth, '% MoM');

        // CEO Trend Chart
        const filteredCeoData = ceoData.filter(d => d.order_month >= '2017-01-01' && d.order_month <= '2018-08-01');
        new Chart(document.getElementById('ceo-trend-chart'), {
            type: 'line',
            data: {
                labels: filteredCeoData.map(d => d.order_month.slice(0, 7)),
                datasets: [
                    {
                        label: 'Monthly Revenue (BRL)',
                        data: filteredCeoData.map(d => d.total_revenue),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Monthly Orders',
                        data: filteredCeoData.map(d => d.total_orders),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    ...chartDefaults.scales,
                    y: { ...chartDefaults.scales.y, position: 'left' },
                    y1: { ...chartDefaults.scales.y, position: 'right', grid: { drawOnChartArea: false } }
                }
            }
        });

        // Top 5 Problems Table (CEO)
        const problemsTable = document.getElementById('ceo-problems-table');
        rootCause.slice(0, 5).forEach(route => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${route.seller_state}</strong> ➔ <strong>${route.customer_state}</strong></td>
                <td>${formatNum(route.total_deliveries)}</td>
                <td><span class="badge badge-danger">${route.late_delivery_rate_pct}%</span></td>
                <td>${route.carrier_fault_share_pct > 60 ? '🚚 Carrier Delays' : '🏭 Slow Sellers'}</td>
            `;
            problemsTable.appendChild(tr);
        });

        // --- 3. RENDER OPERATIONS VIEW ---
        document.getElementById('ops-otd').innerText = `${activeOpsMonth.otd_pct}%`;
        document.getElementById('ops-days').innerText = `${activeOpsMonth.avg_delivery_days} days`;
        document.getElementById('ops-late-rate').innerText = `${activeOpsMonth.late_delivery_rate_pct}%`;
        
        const otdChange = activeOpsMonth.otd_pct - prevOpsMonth.otd_pct;
        renderDeltaBadge('ops-otd-status', otdChange, '% MoM');
        
        const daysChange = activeOpsMonth.avg_delivery_days - prevOpsMonth.avg_delivery_days;
        renderDeltaBadge('ops-days-status', daysChange, ' days MoM', true); // lower is better
        
        const lateChange = activeOpsMonth.late_delivery_rate_pct - prevOpsMonth.late_delivery_rate_pct;
        renderDeltaBadge('ops-late-status', lateChange, '% MoM', true); // lower is better

        // Ops SLA Trend Chart
        const filteredOpsData = opsData.filter(d => d.order_month >= '2017-01-01' && d.order_month <= '2018-08-01');
        new Chart(document.getElementById('ops-sla-chart'), {
            type: 'line',
            data: {
                labels: filteredOpsData.map(d => d.order_month.slice(0, 7)),
                datasets: [
                    {
                        label: 'Avg Delivery Days',
                        data: filteredOpsData.map(d => d.avg_delivery_days),
                        borderColor: '#f59e0b',
                        borderWidth: 3,
                        fill: false
                    },
                    {
                        label: 'SLA Limit (10 days)',
                        data: Array(filteredOpsData.length).fill(10),
                        borderColor: 'rgba(239, 68, 68, 0.5)',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: chartDefaults
        });

        // Ops Root Cause Chart
        const topRoutes = rootCause.slice(0, 8);
        new Chart(document.getElementById('ops-root-cause-chart'), {
            type: 'bar',
            data: {
                labels: topRoutes.map(r => `${r.seller_state}➔${r.customer_state}`),
                datasets: [
                    {
                        label: 'Seller Fault Share (%)',
                        data: topRoutes.map(r => r.seller_fault_share_pct),
                        backgroundColor: 'rgba(99, 102, 241, 0.85)'
                    },
                    {
                        label: 'Carrier Fault Share (%)',
                        data: topRoutes.map(r => r.carrier_fault_share_pct),
                        backgroundColor: 'rgba(16, 185, 129, 0.85)'
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    ...chartDefaults.scales,
                    x: { stacked: true },
                    y: { stacked: true, max: 100 }
                }
            }
        });

        // --- 4. RENDER MARKETING VIEW ---
        const activeMktMonth = marketingData.find(d => d.order_month === '2018-08-01') || marketingData[marketingData.length - 2];
        const prevMktMonth = marketingData.find(d => d.order_month === '2018-07-01') || marketingData[marketingData.length - 3];
        
        document.getElementById('mkt-repeat').innerText = `${activeMktMonth.repeat_order_share_pct}%`;
        document.getElementById('mkt-reviews').innerText = `${activeMktMonth.avg_review_score} / 5`;
        document.getElementById('mkt-acquisition').innerText = formatNum(activeMktMonth.new_customers_acquired);

        const repeatChange = activeMktMonth.repeat_order_share_pct - prevMktMonth.repeat_order_share_pct;
        renderDeltaBadge('mkt-repeat-status', repeatChange, '% MoM');
        
        const reviewsChange = activeMktMonth.avg_review_score - prevMktMonth.avg_review_score;
        renderDeltaBadge('mkt-reviews-status', reviewsChange, ' score MoM');
        
        const acquisitionGrowth = ((activeMktMonth.new_customers_acquired - prevMktMonth.new_customers_acquired) / prevMktMonth.new_customers_acquired) * 100;
        renderDeltaBadge('mkt-acquisition-status', acquisitionGrowth, '% MoM');

        // RFM Segment Distribution
        new Chart(document.getElementById('mkt-rfm-chart'), {
            type: 'bar',
            data: {
                labels: rfmSummary.map(s => s.rfm_segment),
                datasets: [{
                    label: 'Customer Count',
                    data: rfmSummary.map(s => s.customer_count),
                    backgroundColor: '#6366f1',
                    borderRadius: 8
                }]
            },
            options: chartDefaults
        });

        // Cohort Retention (Plotting Jan 2017 Cohort: Month 1 to Max Month)
        const janCohortRaw = cohortData.filter(d => d.cohort_month === '2017-01-01');
        const maxCohortIndex = Math.max(...janCohortRaw.map(d => d.cohort_index), 12);
        
        // Dynamically build a complete timeline of months (filling gaps with 0% retention)
        const janCohortFull = [];
        for (let i = 1; i <= maxCohortIndex; i++) {
            const match = janCohortRaw.find(d => d.cohort_index === i);
            janCohortFull.push({
                cohort_index: i,
                retention_pct: match ? match.retention_pct : 0.00
            });
        }

        new Chart(document.getElementById('mkt-retention-chart'), {
            type: 'line',
            data: {
                labels: janCohortFull.map(c => `Month ${c.cohort_index}`),
                datasets: [{
                    label: 'Retention % (Jan 2017 Cohort: Month 1 to ' + maxCohortIndex + ')',
                    data: janCohortFull.map(c => c.retention_pct),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.2
                }]
            },
            options: {
                ...chartDefaults,
                scales: {
                    ...chartDefaults.scales,
                    y: { max: 1.2, min: 0 } // zooms in on low retention values
                }
            }
        });

        // --- 5. RENDER GEO & CATEGORY VIEW ---
        // State Revenue chart
        new Chart(document.getElementById('geo-state-chart'), {
            type: 'bar',
            data: {
                labels: geoRevenue.map(g => g.state),
                datasets: [{
                    label: 'Revenue (BRL)',
                    data: geoRevenue.map(g => g.revenue),
                    backgroundColor: '#6366f1',
                    borderRadius: 6
                }]
            },
            options: chartDefaults
        });

        // Category performance scatter overlay
        new Chart(document.getElementById('geo-category-chart'), {
            type: 'bar',
            data: {
                labels: categoryPerformance.map(c => c.category_english.replace(/_/g, ' ')),
                datasets: [
                    {
                        label: 'Revenue (BRL)',
                        data: categoryPerformance.map(c => c.revenue),
                        backgroundColor: 'rgba(99, 102, 241, 0.85)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Avg Customer Rating',
                        data: categoryPerformance.map(c => c.avg_review_score),
                        borderColor: '#ffc107',
                        borderWidth: 3,
                        type: 'line',
                        fill: false,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...chartDefaults,
                scales: {
                    ...chartDefaults.scales,
                    y: { position: 'left' },
                    y1: { position: 'right', min: 3.0, max: 5.0, grid: { drawOnChartArea: false } }
                }
            }
        });

        // Payment trend chart
        const uniqueMonths = [...new Set(paymentTrends.map(t => t.order_month.slice(0, 7)))].filter(m => m >= '2017-01' && m <= '2018-08');
        const paymentTypes = ['credit_card', 'boleto', 'voucher', 'debit_card'];
        const datasets = paymentTypes.map((type, index) => {
            const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];
            return {
                label: type.replace(/_/g, ' '),
                data: uniqueMonths.map(month => {
                    const match = paymentTrends.find(t => t.order_month.slice(0, 7) === month && t.payment_type === type);
                    return match ? match.payment_value : 0;
                }),
                backgroundColor: colors[index],
                fill: true
            };
        });

        new Chart(document.getElementById('geo-payments-chart'), {
            type: 'line',
            data: {
                labels: uniqueMonths,
                datasets: datasets
            },
            options: {
                ...chartDefaults,
                scales: {
                    ...chartDefaults.scales,
                    x: { stacked: true },
                    y: { stacked: true }
                }
            }
        });

    } catch (e) {
        console.error('Error loading dashboard assets:', e);
    }
}

// Helpers for badges
function renderDeltaBadge(elementId, value, suffix, invert = false) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    let isPositive = value >= 0;
    if (invert) isPositive = !isPositive; // For rates where lower is better (e.g. late delivery rate)

    el.innerText = `${value >= 0 ? '+' : ''}${value.toFixed(2)}${suffix}`;
    el.className = `kpi-delta ${isPositive ? 'up' : 'down'}`;
}

function renderStatusIndicator(elementId, isHealthy, text) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    el.innerText = text;
    el.className = `kpi-delta ${isHealthy ? 'neutral' : 'down'}`;
}

// Run on page load
window.addEventListener('DOMContentLoaded', initDashboard);
