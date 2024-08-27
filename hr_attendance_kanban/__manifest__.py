# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

{
    "name": "HR Kanban Attendance",
    "version": "16.0.4.0.0",
    "category": "Human Resources",
    "website": "https://github.com/OCA/hr-attendance",
    "author": "Sozialinfo, Odoo Community Association (OCA), Miika Nissi",
    "maintainers": ["miikanissi"],
    "license": "LGPL-3",
    "installable": True,
    "depends": ["hr_attendance", "hr_holidays"],
    "data": [
        "data/hr_attendance_type_data.xml",
        "views/hr_employee_view.xml",
        "views/hr_attendance_view.xml",
        "views/hr_attendance_type_view.xml",
        "views/hr_attendance_kanban_view.xml",
        "wizard/hr_attendance_kanban_wizard_views.xml",
        "wizard/hr_attendance_kanban_break_views.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_attendance_kanban/static/src/views/**/*.js",
            "hr_attendance_kanban/static/src/views/**/*.xml",
            "hr_attendance_kanban/static/src/views/**/*.scss",
            "hr_attendance_kanban/static/src/scss/hr_attendance_kanban.scss",
        ]
    },
    "post_init_hook": "post_init_hook",
}
