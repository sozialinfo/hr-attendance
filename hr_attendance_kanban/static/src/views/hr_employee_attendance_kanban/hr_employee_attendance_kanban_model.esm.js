/** @odoo-module **/

import {EventBus} from "@odoo/owl";
import {KanbanModel} from "@web/views/kanban/kanban_model";
import {isRelational} from "@web/views/utils";
import {launchCheckInWizard} from "@hr_attendance_kanban/views/launch_check_in_wizard.esm";

class TransactionInProgress extends Error {}

class NoTransactionInProgress extends Error {}

function makeTransactionManager() {
    const bus = new EventBus();
    const transactions = {};
    return {
        start: (id) => {
            if (transactions[id]) {
                throw new TransactionInProgress(
                    `Transaction in progress: commit or abort to start a new one.`
                );
            }
            transactions[id] = true;
            bus.trigger("START");
        },
        commit: (id) => {
            if (!transactions[id]) {
                throw new NoTransactionInProgress(`No transaction in progress.`);
            }
            delete transactions[id];
            bus.trigger("COMMIT");
        },
        abort: (id) => {
            if (!transactions[id]) {
                throw new NoTransactionInProgress(`No transaction in progress.`);
            }
            delete transactions[id];
            bus.trigger("ABORT");
        },
        register: ({onStart, onCommit, onAbort}) => {
            let currentData = null;
            bus.addEventListener("START", () => onStart && (currentData = onStart()));
            bus.addEventListener("COMMIT", () => onCommit && onCommit(currentData));
            bus.addEventListener("ABORT", () => onAbort && onAbort(currentData));
        },
    };
}

export class HrEmployeeAttendanceKanbanModel extends KanbanModel {
    setup(params, {orm, action}) {
        super.setup(...arguments);
        this.ormService = orm;
        this.actionService = action;
        this.transaction = makeTransactionManager();
    }
}

export class HrEmployeeAttendanceKanbanDynamicGroupList extends HrEmployeeAttendanceKanbanModel.DynamicGroupList {
    async handleAttendanceChange(record, targetValue) {
        // Check if we need to launch check in/out wizard depending on employee's
        // current attendance state and target attendance type
        const isLaunchCheckIn = await this.model.ormService.call(
            "hr.employee",
            "is_launch_check_in_wizard",
            [record.resId, targetValue[0]]
        );

        // Launch wizard and wait for a callback
        if (isLaunchCheckIn) {
            const closed = await launchCheckInWizard(
                this.model.ormService,
                this.model.actionService,
                record.resId,
                targetValue[0],
                false
            );

            // Abort attendance change if wizard is canceled or exits without save
            if (!closed || closed.special) {
                return false;
            }
            // If no need to launch wizard, save the target attendance type value
        } else {
            await record.update(
                {[this.groupByField.name]: targetValue},
                {silent: true}
            );
            const saved = await record.save({noReload: true});
            if (!saved) {
                return false;
            }
        }
        return true;
    }
    /**
     * @override
     *
     * If the kanban view is grouped by attendance_type_id check if the record is being moved
     * and launch a check in/out wizard
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const sourceGroup = this.groups.find((g) => g.id === dataGroupId);
        const targetGroup = this.groups.find((g) => g.id === targetGroupId);

        // Groups have been re-rendered, old ids are ignored
        if (!sourceGroup || !targetGroup) {
            return;
        }
        // Return super if not targeting hr.attendance.type group in kanban
        if (
            sourceGroup.resModel !== "hr.attendance.type" ||
            targetGroup.resModel !== "hr.attendance.type"
        ) {
            super.moveRecord(...arguments);
        }

        const record = sourceGroup.list.records.find((r) => r.id === dataRecordId);

        try {
            this.model.transaction.start(dataRecordId);
        } catch (err) {
            if (err instanceof TransactionInProgress) {
                return;
            }
            throw err;
        }

        // Move from one group to another
        if (dataGroupId !== targetGroupId) {
            const refIndex = targetGroup.list.records.findIndex((r) => r.id === refId);
            // Quick update: moves the record at the right position and notifies components
            targetGroup.addRecord(sourceGroup.removeRecord(record), refIndex + 1);
            const targetValue = isRelational(this.groupByField)
                ? [targetGroup.value, targetGroup.displayName]
                : targetGroup.value;

            const abort = () => {
                this.model.transaction.abort(dataRecordId);
                this.model.notify();
            };

            try {
                const attendanceChanged = await this.handleAttendanceChange(
                    record,
                    targetValue,
                    abort
                );
                if (!attendanceChanged) {
                    abort();
                    this.model.notify();
                    return;
                }
            } catch (err) {
                abort();
                throw err;
            }

            const promises = [];
            const groupsToReload = [sourceGroup];
            if (!targetGroup.isFolded) {
                groupsToReload.push(targetGroup);
                promises.push(record.load());
            }
            promises.push(this.updateGroupProgressData(groupsToReload, true));
            await Promise.all(promises);
        }

        if (!targetGroup.isFolded) {
            // Only trigger resequence if the group isn't folded
            await targetGroup.list.resequence(dataRecordId, refId);
        }
        this.model.notify();

        this.model.transaction.commit(dataRecordId);

        return true;
    }
}

HrEmployeeAttendanceKanbanModel.DynamicGroupList =
    HrEmployeeAttendanceKanbanDynamicGroupList;
HrEmployeeAttendanceKanbanModel.services = [...KanbanModel.services, "orm", "action"];
