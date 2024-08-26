// frappe.ui.form.on("Sales Invoice", {
//     onload: function(frm) {
//         updateAccountHead(frm);
//     },

//     company: function(frm) {
//         // clear taxes table when company changes
//         frm.doc.taxes = [];
//         frm.refresh_field('taxes');
//         updateAccountHead(frm);
//     }
    
// });

// frappe.ui.form.on("Sales Taxes and Charges ", {

//     custom_add_or_deduct: function(frm) {
//         updateAccountHead(frm);
//     }
    
// });

// function updateAccountHead(frm) {
//     frappe.call({
//         method: 'retention_accounting.public.js.custom_scripts.sales_invoice_custom.get_accounts',
//         args: {
//             company: frm.doc.company
//         },
//         callback: function(r) {
//             if (!r.exc) {
//                 let accounts = r.message;

//                 frm.set_query("account_head", "taxes", function() {
//                     return {
//                         filters: {
//                             name: ['in', accounts]
//                         }
//                     };
//                 });
//             }
//         }
//     });
// }

// frappe.ui.form.on("Sales Taxes and Charges", {
//     custom_add_or_deduct: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if (row.custom_add_or_deduct === 'Deduct') {
//             updateAccountHead(frm);
//         }
//         frm.refresh_field("taxes");
//     }
// });

// function updateAccountHead(frm) {
//     frappe.call({
//         method: 'retention_accounting.public.js.custom_scripts.sales_invoice_custom.get_accounts',
//         args: {
//             company: frm.doc.company
//         },
//         callback: function(r) {
//             if (!r.exc) {
//                 let accounts = r.message;
//                 frm.set_query("account_head", "taxes", function() {
//                     return {
//                         filters: {
//                             name: ['in', accounts]
//                         }
//                     };
//                 });
//             }
//         }
//     });
// }



frappe.ui.form.on("Sales Taxes and Charges", {
    add_deduct_tax: function(frm, cdt, cdn) {
        // clear account_head and description
        frappe.model.set_value(cdt, cdn, "account_head", "");
        frappe.model.set_value(cdt, cdn, "description", "");
        frappe.model.set_value(cdt, cdn, "tax_amount", "");

        let row = locals[cdt][cdn];
        let add_or_deduct = row.add_deduct_tax;
        updateAccountHead(frm, cdt, cdn, add_or_deduct);
    }
});

function updateAccountHead(frm, cdt, cdn, add_or_deduct) {
    frappe.call({
        method: 'retention_accounting.public.js.custom_scripts.sales_invoice_custom.get_accounts',
        args: {
            company: frm.doc.company,
            add_or_deduct: add_or_deduct
        },
        callback: function(r) {
            if (!r.exc) {
                let accounts = r.message;
                let grid_row = frm.fields_dict["taxes"].grid.get_row(cdn);
                grid_row.get_field("account_head").get_query = function() {
                    return {
                        filters: {
                            name: ['in', accounts]
                        }
                    };
                };
                grid_row.refresh_field("account_head");
            }
        }
    });
}