# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_type_id = fields.Many2one(
        "hr.attendance.type",
        string="Attendance Type",
        group_expand="_read_attendance_type_ids",
        compute="_compute_attendance_type_id",
        store=True,
        readonly=False,
        groups="hr_attendance.group_hr_attendance",
    )
    last_attendance_comment = fields.Char(
        related="last_attendance_id.comment",
        store=True,
        groups="hr_attendance.group_hr_attendance",
    )

    @api.depends(
        "last_attendance_id.check_in",
        "last_attendance_id.check_out",
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
            employee_id = ctx.get("default_employee_id")
            employee = (
                self.env["hr.employee"].browse([employee_id]) if employee_id else False
            )
            next_attendance_type_id = ctx.get("default_next_attendance_type_id")
            next_attendance_type = (
                self.env["hr.attendance.type"].browse([next_attendance_type_id])
                if next_attendance_type_id
                else False
            )

            if not employee:
                raise UserError(
                    _("A valid employee must be selected to check in / out.")
                )
            if not next_attendance_type:
                raise UserError(_("Employee must be moved to a valid attendance type."))

            if (
                employee.attendance_state != "checked_out"
                and not next_attendance_type.absent
            ):
                raise UserError(
                    _(
                        "Employee is already checked in, employee must be moved to an"
                        " absent attendance type to check out."
                    )
                )

            if (
                employee.attendance_state != "checked_in"
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
