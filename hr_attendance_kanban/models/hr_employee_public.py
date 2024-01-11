# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    attendance_type_id = fields.Many2one(
        "hr.attendance.type",
        string="Attendance Type",
        group_expand="_read_attendance_type_ids",
        compute="_compute_attendance_type_id",
        store=True,
        readonly=False,
        groups="hr_attendance.group_hr_attendance_kiosk,hr_attendance.group_hr_attendance,hr.group_hr_user",  # noqa:B950
    )
    last_attendance_comment = fields.Char(
        related="employee_id.last_attendance_comment",
        readonly=True,
        groups="hr_attendance.group_hr_attendance,hr.group_hr_user",
    )
    last_check_in = fields.Datetime(
        related="employee_id.last_check_in",
        readonly=True,
        groups="hr_attendance.group_hr_attendance,hr.group_hr_user",
    )
    last_check_out = fields.Datetime(
        related="employee_id.last_check_out",
        readonly=True,
        groups="hr_attendance.group_hr_attendance,hr.group_hr_user",
    )

    @api.depends("employee_id.attendance_type_id")
    def _compute_attendance_type_id(self):
        """Gets the public employee attendance type from the employee"""
        for public_employee in self:
            public_employee.attendance_type_id = (
                public_employee.employee_id.attendance_type_id
            )

    def action_update_attendance_type(self, next_attendance_type_id):
        """
        Checks if Check In / Out wizard needs to be launched for updating records
        attendance type. If changing attendance type without checking out we don't need
        to launch wizard and we save the attendance type.
        :returns: True or False depending on if wizard needs to be launched
        """
        self.ensure_one()
        self.check_attendance_access()

        next_attendance_type = (
            self.env["hr.attendance.type"].browse([next_attendance_type_id])
            if next_attendance_type_id
            else False
        )
        if (
            self.attendance_state == "checked_in"
            and next_attendance_type
            and not next_attendance_type.absent
            and self.attendance_type_id != next_attendance_type
        ):
            # Write as sudo since we already check to ensure attendance access and this
            # enables regular employee users to modify their own attendance
            self.employee_id.sudo().write(
                {"attendance_type_id": next_attendance_type.id}
            )
            return False
        return True

    @api.model
    def action_check_in_out_wizard(self, manual_mode=True):
        """Action to open check in / check out wizard"""
        ctx = dict(self.env.context)
        wizard_action = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_attendance_kanban.hr_attendance_kanban_wizard_action"
        )

        if manual_mode:
            ctx.update({"default_manual_mode": True})
        else:
            public_employee_id = ctx.get("default_public_employee_id")
            public_employee = (
                self.env["hr.employee.public"].browse([public_employee_id])
                if public_employee_id
                else False
            )
            public_employee.check_attendance_access()

            next_attendance_type_id = ctx.get("default_next_attendance_type_id")
            next_attendance_type = (
                self.env["hr.attendance.type"].browse([next_attendance_type_id])
                if next_attendance_type_id
                else False
            )

            if not public_employee:
                raise UserError(
                    _("A valid employee must be selected to check in / out.")
                )
            if not next_attendance_type:
                raise UserError(_("Employee must be moved to a valid attendance type."))

            if (
                public_employee.attendance_state != "checked_out"
                and not next_attendance_type.absent
            ):
                raise UserError(
                    _(
                        "Employee is already checked in, employee must be moved to an"
                        " absent attendance type to check out."
                    )
                )

            if (
                public_employee.attendance_state != "checked_in"
                and next_attendance_type.absent
            ):
                raise UserError(
                    _(
                        "Employee is already checked out, employee must be moved to a"
                        " non-absent attendance type to check in."
                    )
                )

        wizard_action.update(
            {
                "context": ctx,
            }
        )
        return wizard_action

    @api.model
    def _read_attendance_type_ids(self, stages, domain, order):
        attendance_type_ids = self.env["hr.attendance.type"].search([])
        return attendance_type_ids

    def get_attendance_type_id(self):
        self.ensure_one()
        return self.attendance_type_id.id

    def check_attendance_access(self):
        """Check if current user has access to modify employees attendances."""
        self.ensure_one()
        if self.env.user != self.user_id and not self.env.user.has_group(
            "hr_attendance.group_hr_attendance_user"
        ):
            raise AccessError(
                _("Only Officers can manage other employees attendances.")
            )
