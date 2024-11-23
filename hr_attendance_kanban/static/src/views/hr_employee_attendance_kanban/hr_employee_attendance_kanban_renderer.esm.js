/** @odoo-module **/

import {EmployeeInspector} from "../inspector/employee_inspector.esm";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {useRef} from "@odoo/owl";

export class HrEmployeeAttendanceKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.root = useRef("root");
    }

    getEmployeeInspectorProps() {
        // Modify any props here
        return {
            selection: this.props.list.selection,
        };
    }
}

HrEmployeeAttendanceKanbanRenderer.template =
    "hr_attendance_kanban.HrEmployeeAttendanceKanbanRenderer";
HrEmployeeAttendanceKanbanRenderer.components = Object.assign(
    {},
    KanbanRenderer.components,
    {
        EmployeeInspector,
    }
);
