/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {TimeOffCard} from "@hr_holidays/dashboard/time_off_card";
import fieldUtils from "web.field_utils";
import {session} from "@web/session";

export class EmployeeInspector extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            employee: {},
            holidays: [],
        });

        useBus(this.env.model, "update", async () => {
            await this.getEmployeeDays();
        });

        onWillStart(async () => {
            await this.getEmployeeDays();
        });
    }

    async getEmployeeDays() {
        const context = {};

        const publicEmployee = await this.orm.searchRead(
            "hr.employee.public",
            [["user_id", "=", session.uid]],
            ["id", "name", "total_overtime"],
            {limit: 1}
        );
        if (publicEmployee.length === 0) {
            return;
        }

        this.state.employee = publicEmployee[0];
        context.employee_id = this.state.employee.id;

        this.state.holidays = await this.orm.call(
            "hr.leave.type",
            "get_days_all_request",
            [],
            {
                context: context,
            }
        );
    }

    formatFloatTime(value) {
        return fieldUtils.format.float_time(value);
    }
}

EmployeeInspector.components = {TimeOffCard};
EmployeeInspector.template = "hr_attendance_kanban.EmployeeInspector";
