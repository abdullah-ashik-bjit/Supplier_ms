/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SupplierDashboard } from "../components/supplier_dashboard";

// Register the dashboard as a client action
registry.category("actions").add("supplier_ms.supplier_dashboard", SupplierDashboard);