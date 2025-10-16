import {EventBus, useSubEnv} from "@odoo/owl";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {launchCheckInWizard} from "@hr_attendance_kanban/views/launch_check_in_wizard.esm";

export class HrEmployeeAttendanceKanbanController extends KanbanController {
    async checkInOutButtonClicked() {
        const closed = await launchCheckInWizard(
            this.model.orm,
            this.actionService,
            this.employeeId > 0 ? this.employeeId : false,
            false,
            true
        );

        // Abort attendance change if wizard is canceled or exits without save
        if (!closed || closed.special) {
            return;
        }

        // Refresh the view to reflect the attendance change
        this.model.root.load();
    }

    get employeeId() {
        return this.model.employeeId;
    }

    setup() {
        super.setup(...arguments);
        useSubEnv({
            timeOffBus: new EventBus(),
        });
    }
}
