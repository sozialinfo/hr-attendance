import {onWillStart, useState} from "@odoo/owl";
import {RelationalModel} from "@web/model/relational_model/relational_model";
import {launchCheckInWizard} from "@hr_attendance_kanban/views/launch_check_in_wizard.esm";

export class HrEmployeeAttendanceKanbanModel extends RelationalModel {
    setup() {
        super.setup(...arguments);
        this.state = useState({employeeId: null});
        onWillStart(async () => {
            const employeeId = await this.orm.call(
                "hr.employee",
                "get_contextual_employee_id",
                []
            );
            this.state.employeeId = employeeId;
        });
    }
    get employeeId() {
        return this.state.employeeId;
    }
}

export class HrEmployeeAttendanceKanbanDynamicGroupList extends RelationalModel.DynamicGroupList {
    async handleAttendanceChange(record, targetValue) {
        // Check if we need to launch check in/out wizard depending on employee's
        // current attendance state and target attendance type
        const isLaunchCheckIn = await this.model.orm.call(
            "hr.employee.public",
            "action_update_attendance_type",
            [record.resId, targetValue[0]]
        );

        // Launch wizard and wait for a callback
        if (isLaunchCheckIn) {
            const closed = await launchCheckInWizard(
                this.model.orm,
                this.model.action,
                record.resId,
                targetValue[0],
                false
            );

            // Abort attendance change if wizard is canceled or exits without save
            if (!closed || closed.special) {
                return false;
            }

            this.model.root.load();
        }
        return true;
    }
    /**
     * @override
     *
     * If the kanban view is grouped by attendance_type_id check if the record is being moved
     * and launch a check in/out wizard
     *
     * @param {String} dataRecordId
     * @param {String} dataGroupId
     * @param {String} refId
     * @param {String} targetGroupId
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);
        if (dataGroupId === targetGroupId) {
            // Move a record inside the same group
            await targetGroup.list._resequence(
                targetGroup.list.records,
                this.resModel,
                dataRecordId,
                refId
            );
            return;
        }

        // Move record from a group to another group
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);

        const recordIndex = sourceGroup.list.records.findIndex(
            (r) => r.id === dataRecordId
        );
        const record = sourceGroup.list.records[recordIndex];
        // Step 1: move record to correct position
        const refIndex = targetGroup.list.records.findIndex((r) => r.id === refId);
        const oldIndex = sourceGroup.list.records.findIndex(
            (r) => r.id === dataRecordId
        );

        const sourceList = sourceGroup.list;
        // If the source contains more records than what's loaded, reload it after moving the record
        const mustReloadSourceList =
            sourceList.count > sourceList.offset + sourceList.limit;

        sourceGroup._removeRecords([record.id]);
        targetGroup._addRecord(record, refIndex + 1);
        // Step 2: update record value
        const value =
            targetGroup.groupByField.type === "many2one"
                ? [targetGroup.value, targetGroup.displayName]
                : targetGroup.value;
        const revert = () => {
            targetGroup._removeRecords([record.id]);
            sourceGroup._addRecord(record, oldIndex);
        };
        try {
            const attendanceChanged = await this.handleAttendanceChange(record, value);
            if (!attendanceChanged) {
                return revert();
            }
        } catch (e) {
            // Revert changes
            revert();
            throw e;
        }

        const proms = [];
        if (mustReloadSourceList) {
            const {offset, limit, orderBy, domain} = sourceGroup.list;
            proms.push(sourceGroup.list._load(offset, limit, orderBy, domain));
        }
        if (!targetGroup.isFolded) {
            const targetList = targetGroup.list;
            const records = targetList.records;
            proms.push(
                targetList._resequence(records, this.resModel, dataRecordId, refId)
            );
        }
        return Promise.all(proms);
    }
}

HrEmployeeAttendanceKanbanModel.DynamicGroupList =
    HrEmployeeAttendanceKanbanDynamicGroupList;
