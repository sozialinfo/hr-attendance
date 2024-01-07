# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_type_id = fields.Many2one(
        "hr.attendance.type",
        string="Attendance Type",
        ondelete="restrict",
        help="Represents the type of employee attendance",
        group_expand="_read_group_attendance_type_ids",
    )
    comment = fields.Char(help="Optional comment for attendance")

    @api.model
    def _read_group_attendance_type_ids(self, stages, domain, order):
        return self.env["hr.attendance.type"].search([])
