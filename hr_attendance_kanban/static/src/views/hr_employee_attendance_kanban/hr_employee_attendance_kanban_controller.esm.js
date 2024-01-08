/** @odoo-module **/

import {KanbanController} from "@web/views/kanban/kanban_controller";
import {launchCheckInWizard} from "@hr_attendance_kanban/views/launch_check_in_wizard.esm";

import {session} from "@web/session";
import {useService} from "@web/core/utils/hooks";

export class HrEmployeeAttendanceKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
    }

    async checkInOutButtonClicked() {
        // Attempt to get current users employee record
        const employees = await this.orm.searchRead(
            "hr.employee",
            [["user_id", "=", session.uid]],
            ["id"],
            {limit: 1}
        );

        const closed = await launchCheckInWizard(
            this.model.ormService,
            this.model.actionService,
            employees.length > 0 ? employees[0].id : false,
            false,
            true
        );

        // Abort attendance change if wizard is canceled or exits without save
        if (!closed || closed.special) {
            return;
        }
        // Reload model to display attendance change
        this.model.load();
    }
}
