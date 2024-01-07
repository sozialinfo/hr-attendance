# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import _, api, fields, models
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
        help=(
            "Defines that the Attendance Type represents the employee being absent."
            " Only one Attendance Type can represent 'absent' and exactly one"
            " Attendance Type needs to be defined as 'absent'"
        ),
        copy=False,
    )
    fold = fields.Boolean(string="Folded in Kanban")

    @api.constrains("absent")
    def _constrains_only_one_absent(self):
        for attendance_type in self:
            other_absent_attendance_types = self.env["hr.attendance.type"].search(
                [("id", "!=", attendance_type.id), ("absent", "=", True)]
            )
            if attendance_type.absent and other_absent_attendance_types:
                other_absent_attendance_types.absent = False
            elif not attendance_type.absent and not other_absent_attendance_types:
                raise UserError(
                    _(
                        "You cannot uncheck this Attendance Type as 'absent'. There"
                        " needs to be exactly one Attendance Type with 'absent'"
                        " checked, because it is used to represents absent"
                        " employees. You can however mark another Attendance Type"
                        " as 'absent' and then the flag for this record will"
                        " automatically be removed."
                    )
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_absent(self):
        if any(attendance_type.absent for attendance_type in self):
            raise UserError(
                _(
                    "You cannot delete the Attendance Type marked as 'absent'. There"
                    " needs to be exactly one Attendance Type with 'absent' checked,"
                    " because it is used to represents absent employees."
                )
            )
