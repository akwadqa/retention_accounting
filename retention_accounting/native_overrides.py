import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.utils import get_account_currency, get_payment_ledger_entries, delink_original_entry
from erpnext.accounts.general_ledger import make_acc_dimensions_offsetting_entry, validate_accounting_period, validate_disabled_accounts, \
    process_gl_map, save_entries, make_reverse_gl_entries
from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt


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





# purchase invoice
def make_gl_entries_purchase_invoice(self, gl_entries=None, from_repost=False):
    if not gl_entries:
        gl_entries = self.get_gl_entries()

    if gl_entries:
        update_outstanding = "No" if (cint(self.is_paid) or self.write_off_account) else "Yes"

        if self.docstatus == 1:
            make_gl_entries(
                gl_entries,
                update_outstanding=update_outstanding,
                merge_entries=False,
                from_repost=from_repost,
            )
            self.make_exchange_gain_loss_journal()
        elif self.docstatus == 2:
            provisional_entries = [a for a in gl_entries if a.voucher_type == "Purchase Receipt"]
            make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)
            if provisional_entries:
                for entry in provisional_entries:
                    frappe.db.set_value(
                        "GL Entry",
                        {"voucher_type": "Purchase Receipt", "voucher_detail_no": entry.voucher_detail_no},
                        "is_cancelled",
                        1,
                    )

        if update_outstanding == "No":
            update_outstanding_amt(
                self.credit_to,
                "Supplier",
                self.supplier,
                self.doctype,
                self.return_against if cint(self.is_return) and self.return_against else self.name,
            )

    elif self.docstatus == 2 and cint(self.update_stock) and self.auto_accounting_for_stock:
        make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)




# general_ledger
def make_gl_entries(
	gl_map,
	cancel=False,
	adv_adj=False,
	merge_entries=True,
	update_outstanding="Yes",
	from_repost=False,
):
    if gl_map:
        if not cancel:
            make_acc_dimensions_offsetting_entry(gl_map)
            validate_accounting_period(gl_map)
            validate_disabled_accounts(gl_map)
            gl_map = process_gl_map(gl_map, merge_entries)
            if gl_map and len(gl_map) > 1:
                create_payment_ledger_entry(
                    gl_map,
                    cancel=0,
                    adv_adj=adv_adj,
                    update_outstanding=update_outstanding,
                    from_repost=from_repost,
                )
                save_entries(gl_map, adv_adj, update_outstanding, from_repost)
            # Post GL Map proccess there may no be any GL Entries
            elif gl_map:
                frappe.throw(
                    _(
                        "Incorrect number of General Ledger Entries found. You might have selected a wrong Account in the transaction."
                    )
                )
        else:
            make_reverse_gl_entries(gl_map, adv_adj=adv_adj, update_outstanding=update_outstanding)





def create_payment_ledger_entry(
	gl_entries, cancel=0, adv_adj=0, update_outstanding="Yes", from_repost=0, partial_cancel=False
):
    if gl_entries:
        ple_map = get_payment_ledger_entries(gl_entries, cancel=cancel)

        for entry in ple_map:

            ple = frappe.get_doc(entry)

            if cancel:
                delink_original_entry(ple, partial_cancel=partial_cancel)
            
            is_retention_payable_account = (
                entry.get("account") == 
                frappe.get_value("Company", entry.get("company"), "custom_default_retention_payable_account")
            )
            is_retention_receivable_account = (
                entry.get("account") == 
                frappe.get_value("Company", entry.get("company"), "custom_default_retention_receivable_account")
            )
            if is_retention_payable_account or is_retention_receivable_account:
                update_outstanding = "No"

            ple.flags.ignore_permissions = 1
            ple.flags.adv_adj = adv_adj
            ple.flags.from_repost = from_repost
            ple.flags.update_outstanding = update_outstanding
            ple.submit()