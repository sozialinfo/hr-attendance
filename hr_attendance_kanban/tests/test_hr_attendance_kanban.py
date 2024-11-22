# Copyright 2023 Verein sozialinfo.ch
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

from datetime import datetime, timedelta

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, users
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF


@tagged("post_install", "-at_install", "hr_attendance_kanban")
class TestHrAttendanceKanban(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
            )
        )
        cls.att_type_model = cls.env["hr.attendance.type"]
        cls.user = new_test_user(
            cls.env,
            login="test-user",
            groups="base.group_user,hr_attendance.group_hr_attendance",
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": cls.user.login, "user_id": cls.user.id}
        )
        cls.user_admin = new_test_user(
            cls.env,
            login="test-user-admin",
            groups="base.group_user,hr_attendance.group_hr_attendance_manager",
        )
        cls.admin = cls.env["hr.employee"].create(
            {"name": cls.user_admin.login, "user_id": cls.user_admin.id}
        )
        cls.att_type_absent = cls.att_type_model.create(
            {"name": "Absent", "absent": True}
        )
        cls.att_type_office = cls.att_type_model.create({"name": "Office"})
        cls.att_type_home = cls.att_type_model.create({"name": "Home"})
        cls.att_comment = "Checking in comment"

    @users("test-user")
    def test_employee_check(self):
        """Test employee user can check in and out with attendance kanban wizard"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)

        # Check in
        res = (
            self.env["hr.attendance.kanban.wizard"]
            .create(
                {
                    "public_employee_id": public_employee.id,
                    "next_attendance_type_id": self.att_type_office.id,
                    "start_time": datetime.now().strftime(DF),
                    "comment": self.att_comment,
                }
            )
            .action_change()
        )
        self.assertEqual(public_employee.id, res["infos"]["employeeId"])
        self.assertEqual(
            public_employee.last_attendance_id.id, res["infos"]["attendanceId"]
        )
        self.assertEqual(public_employee.attendance_type_id.id, self.att_type_office.id)
        self.assertEqual(public_employee.last_attendance_comment, self.att_comment)
        self.assertEqual(public_employee.attendance_state, "checked_in")

        # Change attendance type
        public_employee.employee_id.sudo().attendance_type_id = self.att_type_home
        self.assertEqual(
            public_employee.attendance_type_id.id,
            public_employee.last_attendance_id.attendance_type_id.id,
        )

        # Check out
        res = (
            self.env["hr.attendance.kanban.wizard"]
            .create(
                {
                    "public_employee_id": public_employee.id,
                    "next_attendance_type_id": self.att_type_absent.id,
                    "end_time": datetime.now().strftime(DF),
                }
            )
            .action_change()
        )
        self.assertEqual(public_employee.id, res["infos"]["employeeId"])
        self.assertEqual(
            public_employee.last_attendance_id.id, res["infos"]["attendanceId"]
        )
        self.assertEqual(public_employee.attendance_type_id.id, self.att_type_absent.id)
        self.assertEqual(public_employee.attendance_state, "checked_out")

    @users("test-user")
    def test_employee_access_own_only(self):
        """Test employee user can't check in other employees"""
        public_admin = self.env["hr.employee.public"].browse(self.admin.ids)
        with self.assertRaises(AccessError):
            self.env["hr.attendance.kanban.wizard"].create(
                {
                    "public_employee_id": public_admin.id,
                    "next_attendance_type_id": self.att_type_office.id,
                    "start_time": datetime.now().strftime(DF),
                }
            ).action_change()
        with self.assertRaises(AccessError):
            self.env["hr.attendance.kanban.break"].create(
                {
                    "public_employee_id": public_admin.id,
                    "start_time": datetime.now().strftime(DF),
                }
            ).action_start_break()

    @users("test-user-admin")
    def test_attendance_type(self):
        """Tests to see that only one absent type exists and absent type can not
        be unlinked."""

        # Ensure only one absent type
        self.assertTrue(self.att_type_absent.absent)
        new_att_type_absent = self.env["hr.attendance.type"].create(
            {"name": "New Absent", "absent": True}
        )
        self.assertTrue(new_att_type_absent.absent)
        self.assertFalse(self.att_type_absent.absent)

        # Test absent type unlink raises UserError
        with self.assertRaises(UserError):
            new_att_type_absent.unlink()

    @users("test-user-admin")
    def test_attendance_manual(self):
        """Test employee attendance type when attendance is created, checked out and
        deleted manually"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)

        # Create attendance manually
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": public_employee.employee_id.id,
                "check_in": datetime.now().strftime(DF),
                "attendance_type_id": self.att_type_office.id,
            }
        )

        # Ensure employee attendance type matches new ongoing attendance
        self.assertEqual(
            attendance.attendance_type_id, public_employee.attendance_type_id
        )

        # Check out attendance
        attendance.check_out = datetime.now().strftime(DF)

        # Ensure employee attendance went back to absent
        self.assertEqual(self.att_type_absent, public_employee.attendance_type_id)

        # Modify attendance to force it back to checked in
        attendance.check_out = False

        # Ensure employee attendance type matches new ongoing attendance
        self.assertEqual(
            attendance.attendance_type_id, public_employee.attendance_type_id
        )

        # Delete the ongoing attendance
        attendance.unlink()

        # Ensure employee attendance went back to absent
        self.assertEqual(self.att_type_absent, public_employee.attendance_type_id)

    @users("test-user")
    def test_employee_break(self):
        """Test employee user can start and end a break in attendance kanban"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)

        check_in_time = datetime.now()

        # Check in
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_office.id,
                "start_time": check_in_time.strftime(DF),
                "comment": self.att_comment,
            }
        ).action_change()

        # Add 30 minutes
        break_start_time = check_in_time + timedelta(minutes=30)

        # Start break
        self.env["hr.attendance.kanban.break"].create(
            {
                "public_employee_id": public_employee.id,
                "start_time": break_start_time.strftime(DF),
            }
        ).action_start_break()

        self.assertEqual(
            public_employee.break_start_time,
            public_employee.last_attendance_id.break_start_time,
        )
        self.assertEqual(
            public_employee.break_start_time, break_start_time.replace(microsecond=0)
        )

        # Add 30 minutes
        break_end_time = break_start_time + timedelta(minutes=30)

        # End break
        first_attendance = public_employee.last_attendance_id
        self.env["hr.attendance.kanban.break"].create(
            {
                "public_employee_id": public_employee.id,
                "end_time": break_end_time.strftime(DF),
            }
        ).action_end_break()

        self.assertEqual(
            public_employee.break_start_time,
            public_employee.last_attendance_id.break_start_time,
        )
        self.assertFalse(public_employee.break_start_time)

        # Ensure the first attendance has ended and there is a new attendance
        attendances = self.env["hr.attendance"].search(
            [("employee_id", "=", public_employee.employee_id.id)]
        )
        self.assertEqual(len(attendances), 2)
        self.assertNotEqual(first_attendance.id, public_employee.last_attendance_id.id)
        self.assertEqual(
            first_attendance.check_out, break_start_time.replace(microsecond=0)
        )
        self.assertEqual(
            public_employee.last_attendance_id.check_in,
            break_end_time.replace(microsecond=0),
        )

        # Add 8 hours since check in
        check_out_time = check_in_time + timedelta(hours=8)

        # Check out
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_absent.id,
                "end_time": check_out_time.strftime(DF),
            }
        ).action_change()

        self.assertEqual(
            public_employee.break_start_time,
            public_employee.last_attendance_id.break_start_time,
        )
        self.assertFalse(public_employee.break_start_time)
        self.assertEqual(first_attendance.worked_hours, 0.5)
        self.assertEqual(public_employee.last_attendance_id.worked_hours, 7.0)

    @users("test-user")
    def test_start_break_when_already_on_break(self):
        """Test employee user cannot start a break when already on a break"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_office.id,
                "start_time": datetime.now().strftime(DF),
                "comment": self.att_comment,
            }
        ).action_change()
        self.env["hr.attendance.kanban.break"].create(
            {
                "public_employee_id": public_employee.id,
                "start_time": (datetime.now() + timedelta(minutes=30)).strftime(DF),
            }
        ).action_start_break()
        with self.assertRaises(UserError):
            self.env["hr.attendance.kanban.break"].create(
                {
                    "public_employee_id": public_employee.id,
                    "start_time": (datetime.now() + timedelta(minutes=60)).strftime(DF),
                }
            ).action_start_break()

    @users("test-user")
    def test_end_break_when_not_on_break(self):
        """Test employee user cannot end a break when not on a break"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_office.id,
                "start_time": datetime.now().strftime(DF),
                "comment": self.att_comment,
            }
        ).action_change()
        with self.assertRaises(UserError):
            self.env["hr.attendance.kanban.break"].create(
                {
                    "public_employee_id": public_employee.id,
                    "end_time": (datetime.now() + timedelta(minutes=30)).strftime(DF),
                }
            ).action_end_break()

    @users("test-user")
    def test_check_in_when_already_checked_in(self):
        """Test employee user cannot check in when already checked in"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_office.id,
                "start_time": datetime.now().strftime(DF),
                "comment": self.att_comment,
            }
        ).action_change()
        with self.assertRaises(UserError):
            self.env["hr.attendance.kanban.wizard"].create(
                {
                    "public_employee_id": public_employee.id,
                    "next_attendance_type_id": self.att_type_home.id,
                    "start_time": datetime.now().strftime(DF),
                    "comment": self.att_comment,
                }
            ).action_change()

    @users("test-user")
    def test_check_out_when_already_checked_out(self):
        """Test employee user cannot check out when already checked out"""
        public_employee = self.env["hr.employee.public"].browse(self.employee.ids)
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_office.id,
                "start_time": datetime.now().strftime(DF),
                "comment": self.att_comment,
            }
        ).action_change()
        self.env["hr.attendance.kanban.wizard"].create(
            {
                "public_employee_id": public_employee.id,
                "next_attendance_type_id": self.att_type_absent.id,
                "end_time": (datetime.now() + timedelta(hours=8)).strftime(DF),
            }
        ).action_change()
        with self.assertRaises(UserError):
            self.env["hr.attendance.kanban.wizard"].create(
                {
                    "public_employee_id": public_employee.id,
                    "next_attendance_type_id": self.att_type_absent.id,
                    "end_time": (datetime.now() + timedelta(hours=9)).strftime(DF),
                }
            ).action_change()
