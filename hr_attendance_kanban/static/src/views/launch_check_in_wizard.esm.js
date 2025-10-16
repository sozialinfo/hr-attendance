export async function launchCheckInWizard(
    orm,
    actionService,
    publicEmployeeId = false,
    nextAttendanceTypeId = false,
    manualMode = false
) {
    const action = await orm.call(
        "hr.employee.public",
        "action_check_in_out_wizard",
        [manualMode],
        {
            context: {
                default_public_employee_id: publicEmployeeId,
                default_next_attendance_type_id: nextAttendanceTypeId,
            },
        }
    );
    return new Promise((resolve) => {
        actionService.doAction(action, {
            onClose: resolve,
        });
    });
}
