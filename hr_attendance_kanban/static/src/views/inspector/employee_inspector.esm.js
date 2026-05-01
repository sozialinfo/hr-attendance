import {TimeOffDashboard} from "@hr_holidays/dashboard/time_off_dashboard";
import {onWillStart, onWillUpdateProps, useState} from "@odoo/owl";

export class EmployeeInspector extends TimeOffDashboard {
    static template = "hr_attendance_kanban.EmployeeInspector";
    static props = {
        "*": true,
        loadCount: {type: Number, optional: true},
    };

    setup() {
        super.setup();
        this.overtimeState = useState({totalOvertime: 0, isCheckedIn: false});
        onWillStart(() => this._loadOvertime(this.props.employeeId));
        onWillUpdateProps((nextProps) => {
            if (
                nextProps.employeeId !== this.props.employeeId ||
                nextProps.loadCount !== this.props.loadCount
            ) {
                return this._loadOvertime(nextProps.employeeId);
            }
        });
    }

    async _loadOvertime(employeeId) {
        if (!employeeId) return;
        const [records, employees] = await Promise.all([
            this.orm.searchRead(
                "hr.attendance.overtime",
                [["employee_id", "=", employeeId]],
                ["duration"]
            ),
            this.orm.searchRead(
                "hr.employee.public",
                [["id", "=", employeeId]],
                ["attendance_state"],
                {limit: 1}
            ),
        ]);
        this.overtimeState.totalOvertime = records.reduce(
            (sum, r) => sum + (r.duration || 0),
            0
        );
        this.overtimeState.isCheckedIn =
            employees[0]?.attendance_state === "checked_in";
    }

    formatFloatTime(value) {
        const hours = Math.floor(Math.abs(value));
        const minutes = Math.round((Math.abs(value) - hours) * 60);
        const sign = value < 0 ? "-" : "";
        return `${sign}${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    }
}
