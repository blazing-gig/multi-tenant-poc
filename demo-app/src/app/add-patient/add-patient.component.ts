import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { SyncService } from './../services/sync.service';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { StatusDialogComponent } from '../status-dialog/status-dialog.component';

@Component({
  selector: 'app-add-patient',
  templateUrl: './add-patient.component.html',
  styleUrls: ['./add-patient.component.scss']
})
export class AddPatientComponent implements OnInit {

    addPatientForm: FormGroup;

    constructor(
        private dialogRef: MatDialogRef<StatusDialogComponent>,
        private syncService: SyncService,
        private dialog: MatDialog
    ) { }

    ngOnInit() {
        
        this.addPatientForm = new FormGroup({
            email: new FormControl(null, [Validators.required]),
            name: new FormControl(null),
        });
    }

    keyDownFunction(event) {
        if (event.keyCode == 13) {
            this.addPatient(event);
        }
    }

    addPatient(event: any) {
        event.stopPropagation();
        console.log("value is ", this.addPatientForm.value);

        this.syncService.post(
            "/patient/", this.addPatientForm.value
        ).subscribe((res) => {
            console.log("res is ", res);
            this.openStatusDialog({
                closeButtonText: "Ok",
                msg: "The request has been processed successfully. \
                    The page will refresh itself to reflect the changes",
                statusHeaderMsg: "Success"
            });
        
        }, (err) => {
            console.log("err is ", err);
            this.openStatusDialog({
                closeButtonText: "Ok",
                msg: "Please check the form data and try again.",
                statusHeaderMsg: "Oops!"
            });
        });
    }

    openStatusDialog(context: any) {
        const dialogRef = this.dialog.open(
            StatusDialogComponent, {
                height: '200px',
                width: '400px',
                data: context,
                disableClose: true,
                autoFocus: false
            }
        );

        dialogRef.afterClosed().subscribe(result => {
            if (result === "Ok") {
                this.dialogRef.close();
            }
        });
    }


}
