import frappe

@frappe.whitelist()
def get_accounts(company):
    filters = {
        'account_type': ['in', ['Tax', 'Chargeable', 'Income Account', 'Expenses Included In Valuation']],
        'disabled': 0,
        'is_group': 0
    }
    if company:
        filters.update({'company': company})

    accounts = frappe.get_all(
        "Account",
        filters=filters,
        pluck="name"
    )

    if company:
        company_doc = frappe.get_doc("Company", company)
        if company_doc.custom_book_retention_payments and company_doc.custom_default_retention_receivable_account:
            retention_receivable_account = company_doc.custom_default_retention_receivable_account
            accounts.append(retention_receivable_account)

    return accounts