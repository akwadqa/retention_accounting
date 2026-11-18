from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from retention_accounting.retention_accounting.report.accounts_receivable_custom.accounts_receivable_custom import (
	ReceivablePayableReport as AccountsReceivableCustom,
)
from retention_accounting.retention_accounting.report.accounts_receivable_summary_custom.accounts_receivable_summary_custom import (
	ReceivablePayableReportWithProject,
)

REPORT_CLASSES = (AccountsReceivableCustom, ReceivablePayableReportWithProject)


class TestAccountsReceivableCustomAgeing(FrappeTestCase):
	def test_ages_as_on_past_report_date(self):
		report_date = getdate(add_days(nowdate(), -200))

		for report_class in REPORT_CLASSES:
			report = report_class({"report_date": report_date, "calculate_ageing_with": "Report Date"})
			self.assertEqual(report.age_as_on, report_date, report_class.__name__)

	def test_ages_as_on_today_when_selected(self):
		report_date = add_days(nowdate(), -200)

		for report_class in REPORT_CLASSES:
			report = report_class({"report_date": report_date, "calculate_ageing_with": "Today Date"})
			self.assertEqual(report.age_as_on, getdate(nowdate()), report_class.__name__)
