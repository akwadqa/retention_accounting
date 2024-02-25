import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.utils import get_account_currency


# purchase invoice
def make_tax_gl_entries_purchase_invoice(self, gl_entries):
    # tax table gl entries
    valuation_tax = {}

    for tax in self.get("taxes"):
        amount, base_amount = self.get_tax_amounts(tax, None)
        if tax.category in ("Total", "Valuation and Total") and flt(base_amount):
            account_currency = get_account_currency(tax.account_head)

            dr_or_cr = "debit" if tax.add_deduct_tax == "Add" else "credit"

            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": tax.account_head,
                        "against": self.supplier,
                        dr_or_cr: base_amount,
                        dr_or_cr + "_in_account_currency": base_amount
                        if account_currency == self.company_currency
                        else amount,
                        "cost_center": tax.cost_center,
                        "party_type": "Supplier" if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None,
						"party": self.supplier if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None
                    },
                    account_currency,
                    item=tax,
                )
            )
        # accumulate valuation tax
        if (
            self.is_opening == "No"
            and tax.category in ("Valuation", "Valuation and Total")
            and flt(base_amount)
            and not self.is_internal_transfer()
        ):
            if self.auto_accounting_for_stock and not tax.cost_center:
                frappe.throw(
                    _("Cost Center is required in row {0} in Taxes table for type {1}").format(
                        tax.idx, _(tax.category)
                    )
                )
            valuation_tax.setdefault(tax.name, 0)
            valuation_tax[tax.name] += (tax.add_deduct_tax == "Add" and 1 or -1) * flt(base_amount)

    if self.is_opening == "No" and self.negative_expense_to_be_booked and valuation_tax:
        # credit valuation tax amount in "Expenses Included In Valuation"
        # this will balance out valuation amount included in cost of goods sold

        total_valuation_amount = sum(valuation_tax.values())
        amount_including_divisional_loss = self.negative_expense_to_be_booked
        i = 1
        for tax in self.get("taxes"):
            if valuation_tax.get(tax.name):
                if i == len(valuation_tax):
                    applicable_amount = amount_including_divisional_loss
                else:
                    applicable_amount = self.negative_expense_to_be_booked * (
                        valuation_tax[tax.name] / total_valuation_amount
                    )
                    amount_including_divisional_loss -= applicable_amount

                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": tax.account_head,
                            "cost_center": tax.cost_center,
                            "against": self.supplier,
                            "credit": applicable_amount,
                            "remarks": self.remarks or _("Accounting Entry for Stock"),
                            "party_type": "Supplier" if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None,
						    "party": self.supplier if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None
                        },
                        item=tax,
                    )
                )

                i += 1

    if self.auto_accounting_for_stock and self.update_stock and valuation_tax:
        for tax in self.get("taxes"):
            if valuation_tax.get(tax.name):
                gl_entries.append(
                    self.get_gl_dict(
                        {
                            "account": tax.account_head,
                            "cost_center": tax.cost_center,
                            "against": self.supplier,
                            "credit": valuation_tax[tax.name],
                            "remarks": self.remarks or _("Accounting Entry for Stock"),
                            "party_type": "Supplier" if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None,
						    "party": self.supplier if frappe.get_value("Account", tax.account_head, "account_type") == "Payable" else None
                        },
                        item=tax,
                    )
                )





# sales invoice
def make_tax_gl_entries_sales_invoice(self, gl_entries):
    enable_discount_accounting = cint(
        frappe.db.get_single_value("Selling Settings", "enable_discount_accounting")
    )

    for tax in self.get("taxes"):
        amount, base_amount = self.get_tax_amounts(tax, enable_discount_accounting)

        if flt(tax.base_tax_amount_after_discount_amount):
            account_currency = get_account_currency(tax.account_head)

            dr_or_cr = "debit" if frappe.get_value("Account", tax.account_head, "account_type") == "Receivable" else "credit"

            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": tax.account_head,
                        "against": self.customer,
                        dr_or_cr: abs(flt(base_amount, tax.precision("tax_amount_after_discount_amount"))),
                        dr_or_cr + "_in_account_currency": abs(
                            flt(base_amount, tax.precision("base_tax_amount_after_discount_amount"))
                            if account_currency == self.company_currency
                            else flt(amount, tax.precision("tax_amount_after_discount_amount"))
                        ),
                        "cost_center": tax.cost_center,
                        "party_type": "Customer" if frappe.get_value("Account", tax.account_head, "account_type") == "Receivable" else None,
						"party": self.customer if frappe.get_value("Account", tax.account_head, "account_type") == "Receivable" else None
                    },
                    account_currency,
                    item=tax,
                )
            )