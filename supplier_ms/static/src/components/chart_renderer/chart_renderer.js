/** @odoo-module alias=supplier_ms.chart_renderer **/

import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

export class ChartRenderer extends Component {
    static template = "supplier_ms.ChartRenderer";
    static props = {
        type: { type: String },
        data: { type: Object },
        options: { type: Object, optional: true },
        height: { type: Number, optional: true }
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

        onMounted(() => this.initChart());
        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    initChart() {
        if (!this.canvasRef.el) {
            console.error('Canvas element not found');
            return;
        }

        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        try {
            const ctx = this.canvasRef.el.getContext('2d');
            
            if (this.chart) {
                this.chart.destroy();
            }

            console.log('Creating chart:', {
                type: this.props.type,
                data: this.props.data
            });

            this.chart = new Chart(ctx, {
                type: this.props.type,
                data: this.props.data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1000,
                        easing: 'easeInOutQuart'
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                padding: 20,
                                font: {
                                    size: 12,
                                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleFont: {
                                size: 13,
                                weight: 'bold'
                            },
                            bodyFont: {
                                size: 12
                            },
                            padding: 12,
                            cornerRadius: 3,
                            displayColors: true
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error initializing chart:', error);
        }
    }
} 