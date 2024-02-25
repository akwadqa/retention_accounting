import frappe

def set_negative_amount(doc, method):
    if doc.taxes:
        for tax in doc.taxes:
            if frappe.get_value("Account", tax.account_head, "account_type") == "Receivable":
                tax.tax_amount = -abs(tax.tax_amount)