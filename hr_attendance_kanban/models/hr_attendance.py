# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    break_time = fields.Float(help="Duration of the break in hours", default=0.0)
    on_break = fields.Datetime(
        help=(
            "Start time of the break. This is a technical field used to calculate break"
            " time."
        ),
        readonly=True,
    )

    _sql_constraints = [
        (
            "check_break_time_positive",
            "CHECK(break_time >= 0.0)",
            "The break time cannot be negative.",
        ),
    ]

    @api.model
    def _read_group_attendance_type_ids(self, stages, domain, order):
        return self.env["hr.attendance.type"].search([])

    @api.depends("check_in", "check_out", "break_time")
    def _compute_worked_hours(self):
        attendance_with_break = self.filtered(lambda a: a.break_time > 0)
        for attendance in attendance_with_break:
            if attendance.check_out and attendance.check_in:
                delta = attendance.check_out - attendance.check_in
                worked_hours = (delta.total_seconds() / 3600.0) - attendance.break_time
                attendance.worked_hours = max(0.0, worked_hours)
            else:
                attendance.worked_hours = False
        return super(HrAttendance, self - attendance_with_break)._compute_worked_hours()

    def _action_start_break(self, start_time):
        self.write({"on_break": start_time})

    def _action_end_break(self, start_time=None, end_time=None):
        if not end_time:
            self.write({"on_break": False})
            return
        for attendance in self:
            if not attendance.on_break:
                raise UserError(_("Employee is not on break."))
            if not start_time:
                start_time = attendance.on_break
            attendance.write(
                {
                    "break_time": (
                        attendance.break_time
                        + (end_time - start_time).total_seconds() / 3600
                    ),
                    "on_break": False,
                }
            )
