# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression


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
    is_kanban_attendance = fields.Boolean(
        string="Kanban Attendance",
        groups="hr_attendance.group_hr_attendanc,hr.group_hr_user",
    )
    is_cur_user = fields.Boolean(
        string="Is Current User",
        compute="_compute_is_cur_user",
        search="_search_is_cur_user",
        help="Technical field to see if the current user is the user of the record.",
    )

    @api.depends("employee_id.attendance_type_id")
    def _compute_attendance_type_id(self):
        """Gets the public employee attendance type from the employee"""
        for public_employee in self:
            public_employee.attendance_type_id = (
                public_employee.employee_id.attendance_type_id
            )

    @api.depends_context("uid")
    @api.depends("user_id")
    def _compute_is_cur_user(self):
        for public_employee in self:
            if public_employee.user_id.id == self.env.user.id:
                public_employee.is_cur_user = True
            else:
                public_employee.is_cur_user = False

    def _search_is_cur_user(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError("Unsupported search operation on current user")

        if (value and operator == "=") or (not value and operator == "!="):
            return [
                (
                    "id",
                    "in",
                    self.env["hr.employee.public"]
                    .sudo()
                    ._search([("user_id", "=", self.env.uid)]),
                )
            ]

        # easier than a not in on a 2many field (hint: use sudo because of
        # complicated ACL on favorite based on user access on employee)
        return [
            (
                "id",
                "not in",
                self.env["hr.employee.public"]
                .sudo()
                ._search([("user_id", "=", self.env.uid)]),
            )
        ]

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Override to support ordering on is_cur_user.

        Ordering through web client calls search_read with an order parameter set.
        Search_read then calls search. In this override we therefore override search
        to intercept a search without count with an order on is_cur_user.
        In that case we do the search in two steps.

        First step: fill with current users results

          * Search public employees that have the user of the current user.
          * Results of that search will be at the top of returned results. Use limit
            None because we have to search all current user public employees.
          * Finally take only a subset of those public employees to fill with
            results matching asked offset / limit.

        Second step: fill with other results. If first step does not gives results
        enough to match offset and limit parameters we fill with a search on other
        public employees. We keep the asked domain and ordering while filtering out
        already scanned public employees to keep a coherent results.

        All other search and search_read are left untouched by this override to avoid
        side effects. Search_count is not affected by this override.
        """
        if count or not order or "is_cur_user" not in order:
            return super().search(
                args, offset=offset, limit=limit, order=order, count=count
            )
        order_items = [
            order_item.strip().lower()
            for order_item in (order or self._order).split(",")
        ]
        user_asc = any("is_cur_user asc" in item for item in order_items)

        # Search employees that are the current user.
        my_employee_domain = expression.AND([[("user_id", "in", [self.env.uid])], args])
        my_employees_order = ", ".join(
            item for item in order_items if "is_cur_user" not in item
        )
        employee_ids = (
            super()
            .search(
                my_employee_domain,
                offset=0,
                limit=None,
                order=my_employees_order,
                count=count,
            )
            .ids
        )

        # keep only requested window (offset + limit, or offset+)
        my_employee_ids_keep = (
            employee_ids[offset : (offset + limit)] if limit else employee_ids[offset:]
        )
        # keep list of already skipped employee ids to exclude them from future search
        my_employee_ids_skip = (
            employee_ids[: (offset + limit)] if limit else employee_ids
        )

        # do not go further if limit is achieved
        if limit and len(my_employee_ids_keep) >= limit:
            return self.browse(my_employee_ids_keep)

        # Fill with remaining employees. If a limit is given, simply remove count of
        # already fetched. Otherwise keep none. If an offset is set we have to
        # reduce it by already fetch results hereabove. Order is updated to exclude
        # is_cur_user when calling super() .
        employee_limit = (limit - len(my_employee_ids_keep)) if limit else None
        if offset:
            employee_offset = max((offset - len(employee_ids), 0))
        else:
            employee_offset = 0
        employee_order = ", ".join(
            item for item in order_items if "is_cur_user" not in item
        )

        other_employee_res = super().search(
            expression.AND([[("id", "not in", my_employee_ids_skip)], args]),
            offset=employee_offset,
            limit=employee_limit,
            order=employee_order,
            count=count,
        )
        if user_asc in order_items:
            return other_employee_res + self.browse(my_employee_ids_keep)
        else:
            return self.browse(my_employee_ids_keep) + other_employee_res

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

    def action_edit_check_in(self):
        """Action to edit check in record with wizard."""
        self.ensure_one()
        self.check_attendance_access()

        if self.attendance_state != "checked_in":
            return

        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_edit_check_in": True,
                "default_public_employee_id": self.id,
                "default_next_attendance_type_id": self.attendance_type_id.id,
            }
        )

        wizard_action = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_attendance_kanban.hr_attendance_kanban_wizard_action"
        )

        wizard_action.update(
            {
                "context": ctx,
            }
        )
        return wizard_action

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
