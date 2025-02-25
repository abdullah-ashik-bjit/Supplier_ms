odoo.define('supplier_registration.dynamic', ['web.public.widget'], function (require) {
    'use strict';

    var PublicWidget = require('web.public.widget');

    var SupplierRegistration = PublicWidget.Widget.extend({
        selector: '#supplier-registration-form',
        events: {
            'click .next-btn': '_onNextStep',
            'click .prev-btn': '_onPrevStep',
            'click #add-client': '_onAddClient',
            'change input[name="expiry_date"]': '_validateExpiryDate',
            'change .file-upload': '_validateFileSize',
            'submit': '_onFormSubmit',
        },

        start: function () {
            console.log("✅ Supplier Registration JS Loaded Successfully!");
            this.steps = this.$el.find('.step');
            this.currentStep = 0;
            this.clientCount = 1;
            this._showStep(this.currentStep);
        },

        _showStep: function (index) {
            this.steps.addClass('d-none').eq(index).removeClass('d-none');
        },

        _onNextStep: function () {
            if (this.currentStep < this.steps.length - 1) {
                this.currentStep++;
                this._showStep(this.currentStep);
            }
        },

        _onPrevStep: function () {
            if (this.currentStep > 0) {
                this.currentStep--;
                this._showStep(this.currentStep);
            }
        },

        _onAddClient: function () {
            if (this.clientCount < 5) {
                this.clientCount++;
                var $clientContainer = this.$el.find("#client_references");
                var $template = this.$el.find("#client-template").html();
                var $newClient = $($template);
                $newClient.find(".client-title").text("Client " + this.clientCount);
                $clientContainer.append($newClient);
            }
        },

        _validateExpiryDate: function (event) {
            var expiryDate = new Date(event.target.value);
            var today = new Date();
            today.setHours(0, 0, 0, 0);
            var $error = this.$el.find("#expiry-error");

            if (expiryDate < today) {
                $error.show();
                event.target.setCustomValidity("Expired certifications cannot be added.");
            } else {
                $error.hide();
                event.target.setCustomValidity("");
            }
        },

        _validateFileSize: function (event) {
            if (event.target.files[0] && event.target.files[0].size > 1 * 1024 * 1024) {
                alert("File size cannot exceed 1MB!");
                event.target.value = "";
            }
        },

        _onFormSubmit: function (event) {
            var isValid = true;
            var requiredFields = this.$el.find("[required]");

            requiredFields.each(function () {
                if (!this.value.trim()) {
                    isValid = false;
                    $(this).addClass("is-invalid");
                } else {
                    $(this).removeClass("is-invalid");
                }
            });

            if (!isValid) {
                event.preventDefault();
                alert("Please fill in all required fields before submitting.");
            }
        },
    });

    PublicWidget.registry.supplier_registration = SupplierRegistration;
    return SupplierRegistration;
});
