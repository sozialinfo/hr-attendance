# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_type_id = fields.Many2one(
        "hr.attendance.type",
        string="Attendance Type",
        group_expand="_read_attendance_type_ids",
        compute="_compute_attendance_type_id",
        inverse="_inverse_attendance_type_id",
        store=True,
        readonly=False,
        groups="hr_attendance.group_hr_attendance_kiosk,hr_attendance.group_hr_attendance,hr.group_hr_user",  # noqa:B950
    )
    last_attendance_comment = fields.Char(
        related="last_attendance_id.comment",
        store=True,
        groups="hr_attendance.group_hr_attendance_user,hr.group_hr_user",
    )

    @api.depends(
        "last_attendance_id.check_in",
        "last_attendance_id.check_out",
        "last_attendance_id.attendance_type_id",
        "last_attendance_id",
    )
    def _compute_attendance_type_id(self):
        """Gets the employee attendance type from the last attendance if it's not yet
        checked out,otherwise employee is absent."""
        absent_att_type = self.env["hr.attendance.type"].search(
            [("absent", "=", True)], limit=1
        )
        for employee in self:
            att = employee.last_attendance_id.sudo()
            employee.attendance_type_id = (
                employee.last_attendance_id.attendance_type_id
                if att and not att.check_out
                else absent_att_type
            )

    def _inverse_attendance_type_id(self):
        """Sets the attendance type of the current attendance if checked in."""
        for employee in self:
            if (
                employee.attendance_type_id
                and not employee.attendance_type_id.absent
                and employee.attendance_state == "checked_in"
            ):
                employee.last_attendance_id.attendance_type_id = (
                    employee.attendance_type_id
                )

    @api.model
    def _read_attendance_type_ids(self, stages, domain, order):
        attendance_type_ids = self.env["hr.attendance.type"].search([])
        return attendance_type_ids
