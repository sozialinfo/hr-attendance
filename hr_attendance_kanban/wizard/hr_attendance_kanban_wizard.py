# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAttendanceKanbanWizard(models.Model):
    _name = "hr.attendance.kanban.wizard"
    _description = "Hr Attendance Kanban Wizard"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    last_attendance_id = fields.Many2one(related="employee_id.last_attendance_id")
    attendance_state = fields.Selection(related="employee_id.attendance_state")

    next_attendance_type_id = fields.Many2one("hr.attendance.type", "Attendance Type")
    comment = fields.Char(help="Optional comment for attendance")

    manual_mode = fields.Boolean(
        help=(
            "Helper field passed in context to allow for manual check in of employee"
            " when not dragged from kanban."
        )
    )

    start_time = fields.Datetime(compute="_compute_times", store=True, readonly=False)
    end_time = fields.Datetime(compute="_compute_times", store=True, readonly=False)
    comment = fields.Char(compute="_compute_comment", store=True, readonly=False)

    @api.depends("last_attendance_id.check_in")
    @api.depends("last_attendance_id.check_out")
    @api.depends("last_attendance_id")
    def _compute_times(self):
        """Computes the default start and end times for check in/out wizard rounded
        down to the closest 5 minutes. If employee is checked in, get the checked in
        time for start time."""
        for wizard in self:
            time_now = fields.Datetime.now()
            time_now_rounded = time_now - datetime.timedelta(
                minutes=time_now.minute % 5,
                seconds=time_now.second,
                microseconds=time_now.microsecond,
            )

            if (
                wizard.employee_id
                and wizard.last_attendance_id
                and not wizard.last_attendance_id.check_out
            ):
                wizard.start_time = wizard.last_attendance_id.check_in
                wizard.end_time = time_now_rounded
            else:
                wizard.start_time = time_now_rounded

    @api.depends("last_attendance_id.comment")
    @api.depends("last_attendance_id.check_out")
    @api.depends("last_attendance_id")
    def _compute_comment(self):
        """Computes the default comment for check in/out wizard. When already checked in
        get the current attendance comment, otherwise comment should be empty."""
        for wizard in self:
            if (
                wizard.employee_id
                and wizard.last_attendance_id
                and not wizard.last_attendance_id.check_out
            ):
                wizard.comment = wizard.last_attendance_id.comment
            else:
                wizard.comment = False

    def action_change(self):
        """Action called by wizard to change check in/out status, attendance type,
        and comment."""
        self.ensure_one()

        employee_id = self.employee_id.sudo()
        # Check in by creating a new attendance record
        if self.attendance_state != "checked_in":
            if not self.next_attendance_type_id or self.next_attendance_type_id.absent:
                raise UserError(
                    _(
                        "Cannot perform check out on {empl_name}, employee is already"
                        " checked out."
                    ).format(empl_name=employee_id.name)
                )
            # Need to ensure new attendance does not start earlier or at the same time
            # as previous attendance to prevent hr.attendance record order being incorrect
            if (
                self.last_attendance_id
                and self.start_time <= self.last_attendance_id.check_in
            ):
                raise UserError(
                    _(
                        "Unable to check in {empl_name} earlier than their previous"
                        " attendance started."
                    ).format(empl_name=employee_id.name)
                )
            vals = {
                "employee_id": employee_id.id,
                "check_in": self.start_time,
                "comment": self.comment,
                "attendance_type_id": (
                    self.next_attendance_type_id.id
                    if self.next_attendance_type_id
                    else False
                ),
            }
            attendance = self.env["hr.attendance"].create(vals)
            return {
                "type": "ir.actions.act_window_close",
                "infos": {
                    "attendanceId": attendance.id,
                    "employeeId": employee_id.id,
                },
            }

        # Check out by checking out the current checked in attendance record
        attendance = self.env["hr.attendance"].search(
            [("employee_id", "=", employee_id.id), ("check_out", "=", False)],
            limit=1,
        )
        if attendance:
            attendance.check_out = self.end_time
        else:
            raise UserError(
                _(
                    "Cannot perform check out on {empl_name}, could not find"
                    " corresponding check in. Your attendances have probably been"
                    " modified manually by human resources."
                ).format(empl_name=employee_id.name)
            )
        return {
            "type": "ir.actions.act_window_close",
            "infos": {"attendanceId": attendance.id, "employeeId": employee_id.id},
        }
