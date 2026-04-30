import {EmployeeInspector} from "../inspector/employee_inspector.esm";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";

export class HrEmployeeAttendanceKanbanRenderer extends KanbanRenderer {
    static template = "hr_attendance_kanban.HrEmployeeAttendanceKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        EmployeeInspector,
    };

    getEmployeeInspectorProps() {
        // Modify any props here
        const {model} = this.props.list;
        return {
            employeeId: model.employeeId,
            loadCount: model.loadCount,
        };
    }
}
