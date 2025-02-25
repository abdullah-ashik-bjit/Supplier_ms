/** @odoo-module alias=supplier_ms.kpi_card **/

import { Component } from "@odoo/owl";

export class KPICard extends Component {
    static template = "supplier_ms.KPICard";
    static props = {
        title: { type: String },
        value: { type: [Number, String] },
        icon: { type: String },
        trend: { type: Number, optional: true },
        color: { type: String, optional: true },
        suffix: { type: String, optional: true }
    };

    get trendClass() {
        if (!this.props.trend) return '';
        return this.props.trend > 0 ? 'text-success' : 'text-danger';
    }

    get trendIcon() {
        if (!this.props.trend) return '';
        return this.props.trend > 0 ? 'fa-arrow-up' : 'fa-arrow-down';
    }
} 