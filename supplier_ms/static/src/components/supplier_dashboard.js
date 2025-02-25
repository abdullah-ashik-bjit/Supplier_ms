/** @odoo-module alias=supplier_ms.supplier_dashboard **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KPICard } from "./kpi_card/kpi_card";
import { ChartRenderer } from "./chart_renderer/chart_renderer";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatCurrency as _formatCurrency } from "@web/core/currency";

export class SupplierDashboard extends Component {
    static template = "supplier_ms.SupplierDashboard";
    static components = { KPICard, ChartRenderer };

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.currencyService = useService("currency");
        this.companyService = useService("company");

        this.state = useState({
            supplier: false,
            dateRange: 'this_week',
            metrics: null,
            loading: true,
            error: null,
            productChartData: null,
            trendChartData: null,
            chartJsLoaded: false,
            filteredProducts: null
        });

        this.dateRanges = [
            { id: 'this_week', name: 'This Week' },
            { id: 'last_week', name: 'Last Week' },
            { id: 'last_month', name: 'Last Month' },
            { id: 'last_year', name: 'Last Year' }
        ];

        // Bind methods
        this.refreshData = this.refreshData.bind(this);
        this.onSupplierChange = this.onSupplierChange.bind(this);
        this.onDateRangeChange = this.onDateRangeChange.bind(this);

        onWillStart(async () => {
            try {
                await loadJS('https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js');
                this.state.chartJsLoaded = true;
                console.log('Chart.js loaded successfully');
            } catch (error) {
                console.error('Failed to load Chart.js:', error);
                this.state.error = "Failed to load Chart.js";
            }
            
            await this.loadSuppliers();
            if (this.suppliers?.length) {
                this.state.supplier = this.suppliers[0].id;
                await this.loadMetrics();
            }
        });
    }

    async loadSuppliers() {
        try {
            this.suppliers = await this.orm.searchRead(
                'res.partner',
                [['supplier_rank', '>', 0]],
                ['id', 'name']
            );
        } catch (error) {
            this.state.error = "Failed to load suppliers";
            console.error(error);
        }
    }

    async loadMetrics() {
        this.state.loading = true;
        this.state.error = null;

        try {
            const metrics = await this.orm.call(
                'supplier.dashboard',
                'get_supplier_metrics',
                [this.state.supplier, this.state.dateRange]
            );

            // Add trend calculations
            metrics.rfqTrend = this.calculateTrend(metrics.totalRFQs, metrics.previousRFQs);
            metrics.amountTrend = this.calculateTrend(metrics.totalAmount, metrics.previousAmount);
            metrics.avgOrderTrend = this.calculateTrend(
                metrics.totalAmount / metrics.totalRFQs,
                metrics.previousAmount / metrics.previousRFQs
            );
            metrics.supplierTrend = this.calculateTrend(metrics.activeSuppliers, metrics.previousActiveSuppliers);

            this.state.metrics = metrics;
            this.updateCharts(metrics);
        } catch (error) {
            this.state.error = "Failed to load metrics";
            console.error('Metrics error:', error);
        } finally {
            this.state.loading = false;
        }
    }

    calculateTrend(current, previous) {
        if (!previous) return 0;
        return ((current - previous) / previous) * 100;
    }

    updateCharts(metrics) {
        console.log('Updating charts with:', metrics);
        
        if (!metrics?.productBreakdown?.length) {
            console.warn('No product breakdown data available');
            this.state.productChartData = null;
            this.state.trendChartData = null;
            this.state.categoryBarChart = null;
            this.state.quantityChart = null;
            return;
        }

        // Product breakdown pie chart (top 6 products)
        const sortedProducts = [...metrics.productBreakdown]
            .sort((a, b) => b.amount - a.amount)
            .slice(0, 6);

        this.state.productChartData = {
            labels: sortedProducts.map(p => p.name),
            datasets: [{
                data: sortedProducts.map(p => p.amount),
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',   // Blue
                    'rgba(16, 185, 129, 0.8)',   // Green
                    'rgba(14, 165, 233, 0.8)',   // Sky
                    'rgba(245, 158, 11, 0.8)',   // Amber
                    'rgba(239, 68, 68, 0.8)',    // Red
                    'rgba(168, 85, 247, 0.8)'    // Purple
                ],
                borderColor: '#ffffff',
                borderWidth: 1,
                hoverOffset: 4
            }]
        };

        // Category breakdown bar chart
        const categoryData = Object.entries(metrics.categoryTotals || {})
            .map(([category, amount]) => ({
                category,
                amount
            }))
            .sort((a, b) => b.amount - a.amount);

        this.state.categoryBarChart = {
            labels: categoryData.map(d => d.category),
            datasets: [{
                label: 'Amount by Category',
                data: categoryData.map(d => d.amount),
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1,
                borderRadius: 4,
                maxBarThickness: 40
            }]
        };

        // Product quantity chart (top 8 products)
        const topQuantityProducts = [...metrics.productBreakdown]
            .sort((a, b) => b.quantity - a.quantity)
            .slice(0, 8);

        this.state.quantityChart = {
            labels: topQuantityProducts.map(p => p.name),
            datasets: [{
                label: 'Quantity Ordered',
                data: topQuantityProducts.map(p => p.quantity),
                backgroundColor: 'rgba(16, 185, 129, 0.8)',
                borderColor: 'rgb(16, 185, 129)',
                borderWidth: 1,
                borderRadius: 4,
                maxBarThickness: 40
            }]
        };

        // Weekly trend line chart
        const weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
        const trendData = weeks.map((_, index) => {
            const weekAmount = metrics.productBreakdown.reduce((sum, product) => 
                sum + (product.amount * ((index + 1) / weeks.length)), 0);
            return Math.round(weekAmount * 100) / 100;
        });

        this.state.trendChartData = {
            labels: weeks,
            datasets: [{
                label: 'RFQ Amount Trend',
                data: trendData,
                fill: {
                    target: 'origin',
                    above: 'rgba(59, 130, 246, 0.05)'
                },
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.5)',
                borderWidth: 2,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: 'rgb(59, 130, 246)',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3
            }]
        };

        console.log('Chart data updated:', {
            productChart: this.state.productChartData,
            categoryChart: this.state.categoryBarChart,
            quantityChart: this.state.quantityChart,
            trendChart: this.state.trendChartData
        });
    }

    async onSupplierChange(ev) {
        this.state.supplier = parseInt(ev.target.value);
        await this.loadMetrics();
    }

    async onDateRangeChange(ev) {
        this.state.dateRange = ev.target.value;
        await this.loadMetrics();
    }

    async refreshData() {
        await this.loadMetrics();
    }

    // Update formatCurrency method
    formatCurrency(amount) {
        return _formatCurrency(amount, {
            currencyId: this.companyService.currentCompany.currency_id,
            digits: [69, 2],
        });
    }

    // Add category filter handler
    onCategoryFilter(ev) {
        const category = ev.target.value;
        if (!category) {
            this.state.filteredProducts = null; // Show all products
            return;
        }
        
        this.state.filteredProducts = this.state.metrics.productBreakdown.filter(
            product => product.category === category
        );
    }
} 