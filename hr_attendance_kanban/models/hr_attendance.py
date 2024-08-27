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

    break_start_time = fields.Datetime(
        help=(
            "Start time of the break. This is a technical field used to calculate break"
            " time and determine if an attendance is on break."
        ),
        readonly=True,
    )

    @api.model
    def _read_group_attendance_type_ids(self, stages, domain, order):
        return self.env["hr.attendance.type"].search([])

    @api.constrains("check_out", "check_in", "break_start_time")
    def _check_break_time(self):
        for attendance in self.filtered("break_start_time"):
            if attendance.check_out:
                raise UserError(_("Employee cannot start a break while checked out."))
            elif (
                attendance.check_in
                and attendance.check_in >= attendance.break_start_time
            ):
                raise UserError(_("Employee cannot start a break before checking in."))

    def write(self, vals):
        res = super().write(vals)
        # Ensure that the break is ended when checking out
        if vals.get("check_out"):
            self.filtered(lambda x: x.break_start_time).write(
                {"break_start_time": False}
            )
        return res

    def _action_start_break(self, start_time=None):
        """
        Starts a break for the employee by setting the break_start_time.

        :param start_time: Optional datetime to set as the break_start_time. \
            If not provided, the current datetime is used.
        """
        self.write({"break_start_time": start_time or fields.Datetime.now()})

    def _action_check_out(self, end_time=None):
        """
        Checks out the employee by setting the check_out time resetting the \
        break_start_time.

        :param end_time: Optional datetime to set as the check_out time.
        :raises UserError: If the employee is already checked out.
        """
        self.ensure_one()
        if self.check_out:
            raise UserError(_("Employee is already checked out."))

        self.write(
            {"check_out": end_time or fields.Datetime.now(), "break_start_time": False}
        )
