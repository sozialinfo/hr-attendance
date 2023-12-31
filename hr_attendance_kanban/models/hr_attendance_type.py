# Copyright 2023 Odoo S.A.
# Copyright 2023 ForgeFlow, S.L.
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import fields, models, api
from odoo.exceptions import UserError


class HrAttendanceType(models.Model):
    _name = "hr.attendance.type"
    _description = "Attendance Type"
    _order = "sequence,id"

    sequence = fields.Integer()
    name = fields.Char(
        string="Type",
        help="Represents a lane in the Attendance Kanban Board",
        required=True,
        index=True,
    )
    absent = fields.Boolean(
        string="Absent",
        help="Defines that the Attendance Type represents the employee being absent. Only one Attendance Type can represent 'absent' and exactly one Attendance Type needs to be defined as 'absent'",
        copy=False
    )

    @api.onchange('absent')
    def _check_only_one_absent(self):

        # Get all attendance types which are defined as 'absent'
        absent_attendance_types = self.env['hr.attendance.type'].search(
                [('absent', '=', True)],
                order = 'sequence'
            )

        if len(absent_attendance_types) == 1:

            if absent_attendance_types.id == self.id.origin:
                # This was the only attendance type defined as 'absent' and the user
                # wants to uncheck it. That's a no-go.
                raise UserError("You cannot uncheck this Attendance Type as 'absent'. There needs to be exactly one Attendance Type with 'absent' checked, because it is used to represents absent employees. You can however mark another Attendance Type as 'absent' and then the flag for this record will automatically be removed.")
            else:
                # There was already _another_ attendance type defined as 'absent'.
                # Uncheck that one: there may only ever be one.
                absent_attendance_types.write({'absent': False})

        if len(absent_attendance_types) > 1:
            # This should never happen... but just in case.
            # If there is more than one attendance type as 'absent', just mark the first one.
            absent_attendance_types.write({'absent': False})
            absent_attendance_types[0].write({'absent': True})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_absent(self):
        if any(attendance_type.absent for attendance_type in self):
            raise UserError("You cannot delete the Attendance Type marked as 'absent'. There needs to be exactly one Attendance Type with 'absent' checked, because it is used to represents absent employees.")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for attendance_type in self:
            used_attendance_types = self.env['hr.attendance'].search_count(
                    [('attendance_type_id', '=', attendance_type.id)]
                )
            if used_attendance_types > 0:
                raise UserError("You cannot delete this Attendance Type because it was already used.")
        