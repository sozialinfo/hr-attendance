/** @odoo-module **/

import {KanbanController} from "@web/views/kanban/kanban_controller";

import {session} from "@web/session";
import {useService} from "@web/core/utils/hooks";

export class HrEmployeeAttendanceKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
    }

    async checkInOutButtonClicked() {
        const employees = await this.orm.searchRead(
            "hr.employee",
            [["user_id", "=", session.uid]],
            ["id"],
            {limit: 1}
        );
        const action = await this.orm.call(
            "hr.employee",
            "action_check_in_out_wizard",
            [],
            {
                context: {
                    default_employee_id: employees.length > 0 ? employees[0].id : false,
                },
            }
        );
        await this.action.doAction(action, {
            onClose: () => window.location.reload(),
        });
    }
}
