# Copyright 2017 Odoo S.A.
# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_type_id = fields.Many2one('hr.attendance.type', string='Attendance Type', group_expand='_read_attendance_type_ids', compute='_compute_hr_attendance_type', store=True)

    @api.depends_context('hr.attendance')
    def _compute_hr_attendance_type(self):

        for employee in self:

            # Get the current check-in for the employee. There should always only be one record where the check-out date is empty (Odoo standard)
            latest_attendance = self.env['hr.attendance'].search(
                [('employee_id', '=', employee.id),
                 ('check_out', '=', False)],
                limit=1
            )
            
            if latest_attendance:
                # A record was found. This means the employee is present. Return the attendance type.
                employee.attendance_type_id = latest_attendance.attendance_type_id
            else:
                # No record was found. This means the employee is absent. Return the attendance type which is marked as 'absent'
                absent_attendance_type_id = self.env['hr.attendance.type'].search(
                    [('absent', '=', True)],
                    limit=1
                )
                employee.attendance_type_id = absent_attendance_type_id


    # Make sure all attendance types are displayed in the kanban board
    @api.model
    def _read_attendance_type_ids(self,stages,domain,order):
        attendance_type_ids = self.env['hr.attendance.type'].search([])
        return attendance_type_ids
