/** @odoo-module **/

import {HrEmployeeAttendanceKanbanController} from "@hr_attendance_kanban/views/hr_employee_attendance_kanban/hr_employee_attendance_kanban_controller.esm";
import {HrEmployeeAttendanceKanbanModel} from "@hr_attendance_kanban/views/hr_employee_attendance_kanban/hr_employee_attendance_kanban_model.esm";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

export const hrEmployeeAttendanceKanbanView = {
    ...kanbanView,
    Controller: HrEmployeeAttendanceKanbanController,
    Model: HrEmployeeAttendanceKanbanModel,
    buttonTemplate: "hr_attendance_kanban.HrEmployeeAttendanceKanbanController.Buttons",
};

registry
    .category("views")
    .add("hr_employee_attendance_kanban", hrEmployeeAttendanceKanbanView);
