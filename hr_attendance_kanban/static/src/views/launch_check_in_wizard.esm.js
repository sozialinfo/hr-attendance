/** @odoo-module **/

import {useService} from "@web/core/utils/hooks";

const {useComponent} = owl;

export async function launchCheckInWizard(orm, actionService, recordId, value) {
    const action = await orm.call(
        "hr.employee",
        "action_check_in_out_wizard",
        [false],
        {
            context: {
                default_employee_id: recordId,
                default_next_attendance_type_id: value[0],
            },
        }
    );

    return new Promise((resolve) => {
        actionService.doAction(action, {
            onClose: resolve,
        });
    });
}

export function useCheckInWizard() {
    const component = useComponent();
    const orm = useService("orm");
    const actionService = useService("action");
    return launchCheckInWizard.bind(component, orm, actionService);
}
