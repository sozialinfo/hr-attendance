# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAttendanceKanbanBreak(models.Model):
    _name = "hr.attendance.kanban.break"
    _description = "Hr Attendance Kanban Break"

    public_employee_id = fields.Many2one(
        "hr.employee.public", string="Employee", required=True
    )
    last_attendance_id = fields.Many2one(
        related="public_employee_id.last_attendance_id"
    )
    on_break = fields.Datetime(related="last_attendance_id.on_break")

    attendance_state = fields.Selection(related="public_employee_id.attendance_state")

    start_time = fields.Datetime(
        compute="_compute_start_time",
        store=True,
        readonly=False,
        required=True,
        precompute=True,
    )
    end_time = fields.Datetime(compute="_compute_end_time", store=True, readonly=False)

    @api.depends(
        "on_break",
        "last_attendance_id.on_break",
        "last_attendance_id",
        "public_employee_id",
    )
    def _compute_start_time(self):
        """Computes the default start time for break wizard rounded
        down to the closest 5 minutes. If employee is on break, get the break start in
        time for start time."""
        time_now = fields.Datetime.now()
        time_now_rounded = time_now - datetime.timedelta(
            minutes=time_now.minute % 5,
            seconds=time_now.second,
            microseconds=time_now.microsecond,
        )

        for wizard in self:
            if (
                wizard.public_employee_id
                and wizard.last_attendance_id
                and wizard.on_break
            ):
                wizard.start_time = wizard.on_break
            else:
                wizard.start_time = time_now_rounded

    @api.depends(
        "last_attendance_id",
        "public_employee_id",
    )
    def _compute_end_time(self):
        """Computes the end time for break wizard rounded
        down to the closest 5 minutes when ending break."""
        time_now = fields.Datetime.now()
        time_now_rounded = time_now - datetime.timedelta(
            minutes=time_now.minute % 5,
            seconds=time_now.second,
            microseconds=time_now.microsecond,
        )
        self.end_time = time_now_rounded

    def action_start_break(self):
        """Action called by wizard to start a break."""
        self.ensure_one()
        public_employee_id = self.public_employee_id
        public_employee_id.check_attendance_access()

        self_sudo = self.sudo()

        if self_sudo.on_break:
            raise UserError(
                _(
                    f"Cannot start a break for {public_employee_id.name}, employee is"
                    " already on break."
                )
            )

        if self_sudo.attendance_state != "checked_in":
            raise UserError(
                _(
                    f"Cannot start a break for {public_employee_id.name}, employee is"
                    " not checked in."
                )
            )

        if self_sudo.start_time < self_sudo.last_attendance_id.check_in:
            raise UserError(
                _('"Start Time" time cannot be earlier than "Check In" time.')
            )
        self_sudo.last_attendance_id._action_start_break(self_sudo.start_time)
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "attendanceId": self_sudo.last_attendance_id.id,
                "employeeId": public_employee_id.id,
            },
        }

    def action_end_break(self):
        """Action called by wizard to end a break."""
        self.ensure_one()
        public_employee_id = self.public_employee_id
        public_employee_id.check_attendance_access()

        self_sudo = self.sudo()

        if not self_sudo.on_break:
            raise UserError(
                _(
                    f"Cannot end a break for {public_employee_id.name}, employee is"
                    " not on break."
                )
            )

        if self_sudo.attendance_state != "checked_in":
            raise UserError(
                _(
                    f"Cannot end a break for {public_employee_id.name}, employee is"
                    " not checked in."
                )
            )

        if self_sudo.start_time < self_sudo.last_attendance_id.check_in:
            raise UserError(_('"Start Time" cannot be earlier than "Check In" time.'))

        if not self_sudo.end_time or self_sudo.end_time < self_sudo.start_time:
            raise UserError(_('"End Time" cannot be earlier than "Start Time".'))

        self_sudo.last_attendance_id._action_end_break(
            start_time=self_sudo.start_time, end_time=self_sudo.end_time
        )
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "attendanceId": self_sudo.last_attendance_id.id,
                "employeeId": public_employee_id.id,
            },
        }
