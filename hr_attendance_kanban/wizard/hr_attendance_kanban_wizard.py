# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAttendanceKanbanWizard(models.Model):
    _name = "hr.attendance.kanban.wizard"
    _description = "Hr Attendance Kanban Wizard"

    public_employee_id = fields.Many2one(
        "hr.employee.public", string="Employee", required=True
    )
    last_attendance_id = fields.Many2one(
        related="public_employee_id.last_attendance_id"
    )
    break_start_time = fields.Datetime(related="last_attendance_id.break_start_time")

    attendance_state = fields.Selection(related="public_employee_id.attendance_state")

    next_attendance_type_id = fields.Many2one("hr.attendance.type", "Attendance Type")

    manual_mode = fields.Boolean(
        help=(
            "Helper field passed in context to allow for manual check in of employee"
            " when not dragged from kanban."
        )
    )
    edit_check_in = fields.Boolean(
        help=(
            "Helper field passed in context to allow for editing of employee's"
            " attendance record."
        )
    )
    check_in_mode = fields.Selection(
        [
            ("check_in", "Check In"),
            ("check_out", "Check Out"),
            ("edit_check_in", "Edit Check In"),
        ],
        compute="_compute_check_in_mode",
    )

    start_time = fields.Datetime(
        compute="_compute_start_time",
        store=True,
        readonly=False,
        required=True,
        precompute=True,
    )
    end_time = fields.Datetime(compute="_compute_end_time", store=True, readonly=False)
    comment = fields.Char(compute="_compute_comment", store=True, readonly=False)

    @api.depends(
        "last_attendance_id.check_in",
        "last_attendance_id.check_out",
        "last_attendance_id",
        "public_employee_id",
    )
    def _compute_start_time(self):
        """Computes the default start time for check in/out wizard rounded
        down to the closest minute. If employee is checked in, get the checked in
        time for start time."""
        time_now = fields.Datetime.now()
        time_now_rounded = time_now - datetime.timedelta(
            seconds=time_now.second,
            microseconds=time_now.microsecond,
        )

        for wizard in self:
            if (
                wizard.public_employee_id
                and wizard.last_attendance_id
                and not wizard.last_attendance_id.check_out
            ):
                wizard.start_time = wizard.last_attendance_id.check_in
            else:
                wizard.start_time = time_now_rounded

    @api.depends(
        "last_attendance_id.check_in",
        "last_attendance_id.check_out",
        "last_attendance_id",
        "public_employee_id",
    )
    def _compute_end_time(self):
        """Computes the end time for check in/out wizard rounded
        down to the closest minute when checking out."""
        time_now = fields.Datetime.now()
        time_now_rounded = time_now - datetime.timedelta(
            seconds=time_now.second,
            microseconds=time_now.microsecond,
        )
        for wizard in self:
            if (
                wizard.public_employee_id
                and wizard.last_attendance_id
                and not wizard.last_attendance_id.check_out
            ):
                wizard.end_time = time_now_rounded
            else:
                wizard.end_time = False

    @api.depends(
        "last_attendance_id.comment",
        "last_attendance_id.check_out",
        "last_attendance_id",
        "public_employee_id",
    )
    def _compute_comment(self):
        """Computes the default comment for check in/out wizard. When already checked in
        get the current attendance comment, otherwise comment should be empty."""
        for wizard in self:
            if (
                wizard.public_employee_id
                and wizard.last_attendance_id
                and not wizard.last_attendance_id.check_out
            ):
                wizard.comment = wizard.last_attendance_id.comment
            else:
                wizard.comment = False

    @api.depends("edit_check_in", "public_employee_id")
    def _compute_check_in_mode(self):
        """Computes the check in mode for the wizard based on the context passed in."""
        for wizard in self:
            if wizard.edit_check_in:
                wizard.check_in_mode = "edit_check_in"
            elif wizard.attendance_state == "checked_in":
                wizard.check_in_mode = "check_out"
            elif wizard.attendance_state == "checked_out":
                wizard.check_in_mode = "check_in"
            else:
                wizard.check_in_mode = False

    def action_change(self):
        """Action called by wizard to change check in/out status, attendance type,
        and comment."""
        self.ensure_one()
        public_employee_id = self.public_employee_id
        public_employee_id.check_attendance_access()

        self_sudo = self.sudo()

        # Check in by creating a new attendance record
        if self_sudo.attendance_state != "checked_in":
            if (
                not self_sudo.next_attendance_type_id
                or self_sudo.next_attendance_type_id.absent
            ):
                raise UserError(
                    _(
                        "Cannot perform check out on {empl_name}, employee is already"
                        " checked out."
                    ).format(empl_name=public_employee_id.name)
                )
            # Need to ensure new attendance does not start earlier or at the same time
            # as previous attendance to ensure correct hr.attendance record order
            if (
                self_sudo.last_attendance_id
                and self_sudo.start_time <= self_sudo.last_attendance_id.check_in
            ):
                raise UserError(
                    _(
                        "Unable to check in {empl_name} earlier than their previous"
                        " attendance started."
                    ).format(empl_name=public_employee_id.name)
                )
            vals = {
                "employee_id": public_employee_id.employee_id.id,
                "check_in": self_sudo.start_time,
                "comment": self_sudo.comment,
                "attendance_type_id": (
                    self_sudo.next_attendance_type_id.id
                    if self_sudo.next_attendance_type_id
                    else False
                ),
            }
            attendance = self_sudo.env["hr.attendance"].create(vals)
            return {
                "type": "ir.actions.act_window_close",
                "infos": {
                    "attendanceId": attendance.id,
                    "employeeId": public_employee_id.id,
                },
            }

        # Check out by checking out the current checked in attendance record
        attendance = self_sudo.env["hr.attendance"].search(
            [
                ("employee_id", "=", public_employee_id.employee_id.id),
                ("check_out", "=", False),
            ],
            limit=1,
        )
        if attendance:
            if self_sudo.end_time < attendance.check_in:
                raise UserError(
                    _('"Check Out" time cannot be earlier than "Check In" time.')
                )
            if self_sudo.break_start_time:
                raise UserError(
                    _(
                        "Cannot perform check out on {empl_name} while they are on"
                        " break. Please end the break first."
                    ).format(empl_name=public_employee_id.name)
                )
            attendance._action_check_out(end_time=self_sudo.end_time)
        else:
            raise UserError(
                _(
                    "Cannot perform check out on {empl_name}, could not find"
                    " corresponding check in. Your attendances have probably been"
                    " modified manually by human resources."
                ).format(empl_name=public_employee_id.name)
            )
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "attendanceId": attendance.id,
                "employeeId": public_employee_id.id,
            },
        }

    def action_edit(self):
        """Action called by wizard to change check in time, attendance type,
        and comment."""
        self.ensure_one()
        public_employee_id = self.public_employee_id
        public_employee_id.check_attendance_access()

        self_sudo = self.sudo()

        if self_sudo.attendance_state != "checked_in":
            raise UserError(
                _(
                    f"Cannot edit attendance of {public_employee_id.name} when they are"
                    " not checked in."
                )
            )

        # Get current attendance record
        attendance = self_sudo.env["hr.attendance"].search(
            [
                ("employee_id", "=", public_employee_id.employee_id.id),
                ("check_out", "=", False),
            ],
            limit=1,
        )
        if attendance:
            attendance.write(
                {
                    "check_in": self_sudo.start_time,
                    "comment": self_sudo.comment,
                    "attendance_type_id": self_sudo.next_attendance_type_id.id,
                }
            )
        else:
            raise UserError(
                _(
                    "Cannot edit check in on {empl_name}, could not find"
                    " corresponding check in. Your attendances have probably been"
                    " modified manually by human resources."
                ).format(empl_name=public_employee_id.name)
            )
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "attendanceId": attendance.id,
                "employeeId": public_employee_id.id,
            },
        }
