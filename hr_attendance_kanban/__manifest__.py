# Copyright 2023 Odoo S.A.
# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

{
    "name": "HR Kanban Attendance",
    "version": "16.0.0.0.0",
    "category": "Human Resources",
    "website": "https://github.com/sozialinfo/hr-attendance",
    "author": "Odoo S.A., Sozialinfo, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["hr_attendance"],
    "data": [
        "data/hr_attendance_type_data.xml",
        "views/hr_employee_view.xml",
        "views/hr_attendance_view.xml",
        "views/hr_attendance_type_view.xml",
        "views/hr_attendance_kanban_view.xml",
        "security/ir.model.access.csv"
    ]
}
