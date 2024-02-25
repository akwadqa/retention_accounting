frappe.ui.form.on("Sales Invoice", {
    onload: function(frm) {
        updateAccountHead(frm);
    },

    company: function(frm) {
        // clear taxes table when company changes
        frm.doc.taxes = [];
        frm.refresh_field('taxes');
        updateAccountHead(frm);
    }
    
});

function updateAccountHead(frm) {
    frappe.call({
        method: 'retention_accounting.public.js.custom_scripts.sales_invoice_custom.get_accounts',
        args: {
            company: frm.doc.company
        },
        callback: function(r) {
            if (!r.exc) {
                let accounts = r.message;

                frm.set_query("account_head", "taxes", function() {
                    return {
                        filters: {
                            name: ['in', accounts]
                        }
                    };
                });
            }
        }
    });
}
