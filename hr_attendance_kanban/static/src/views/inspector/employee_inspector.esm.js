import {TimeOffDashboard} from "@hr_holidays/dashboard/time_off_dashboard";
import {onWillStart, onWillUpdateProps, useState} from "@odoo/owl";

export class EmployeeInspector extends TimeOffDashboard {
    static template = "hr_attendance_kanban.EmployeeInspector";

    setup() {
        super.setup();
        this.overtimeState = useState({totalOvertime: 0});
        onWillStart(() => this._loadOvertime(this.props.employeeId));
        onWillUpdateProps((nextProps) => {
            if (nextProps.employeeId !== this.props.employeeId) {
                return this._loadOvertime(nextProps.employeeId);
            }
        });
    }

    async _loadOvertime(employeeId) {
        if (!employeeId) return;
        const employees = await this.orm.searchRead(
            "hr.employee.public",
            [["id", "=", employeeId]],
            ["total_overtime"],
            {limit: 1}
        );
        if (employees.length) {
            this.overtimeState.totalOvertime = employees[0].total_overtime || 0;
        }
    }

    formatFloatTime(value) {
        const hours = Math.floor(Math.abs(value));
        const minutes = Math.round((Math.abs(value) - hours) * 60);
        const sign = value < 0 ? "-" : "";
        return `${sign}${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    }
}
