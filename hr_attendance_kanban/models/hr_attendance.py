# Copyright 2017 Odoo S.A.
# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import fields, models, api
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attendance_type_id = fields.Many2one('hr.attendance.type', string='Attendance Type')
    comment = fields.Char(string="Comment")

    def write(self, vals):
        if 'attendance_type_id' in vals:
            pass
     
        return super(HrAttendance, self).write(vals)

