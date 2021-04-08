import { Component, OnInit, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
    selector: 'app-status-dialog',
    templateUrl: './status-dialog.component.html',
    styleUrls: ['./status-dialog.component.scss']
})
export class StatusDialogComponent implements OnInit {

    constructor(
        @Inject(MAT_DIALOG_DATA) public context: any,
        private dialogRef: MatDialogRef<StatusDialogComponent>
    ) { }

    ngOnInit() {
    }

    closeDialog(event: any) {
        event.stopPropagation();
        this.dialogRef.close(this.context.closeButtonText);
    }

}
