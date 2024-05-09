# Copyright 2024 Miika Nissi (https://miikanissi.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Attendance Configuration Menu",
    "summary": "Redefines the HR Attendance configuration menu",
    "version": "16.0.1.0.0",
    "category": "Human Resources",
    "website": "https://github.com/OCA/hr-attendance",
    "author": "Sozialinfo, Odoo Community Association (OCA), Miika Nissi",
    "maintainers": ["miikanissi"],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "auto_install": True,
    "depends": ["hr_attendance_kanban", "hr_attendance_reason"],
    "data": ["views/hr_attendance_views.xml"],
}
