import { AddPatientComponent } from './../add-patient/add-patient.component';

import { SyncService } from './../services/sync.service';
import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
// import { AddPatientComponent } from '../add-patient/add-patient.component';

@Component({
    selector: 'app-dash',
    templateUrl: './dash.component.html',
    styleUrls: ['./dash.component.scss']
})
export class DashComponent implements OnInit {
    hospitals = null;
    patients = null;

    spinnerValue: number = 0;

    constructor(
        private syncService: SyncService,
        private dialog: MatDialog
    ) { }

    startTimer(): void {
        const x = setInterval(() => {
            this.spinnerValue += 20;
            if(this.spinnerValue === 100) {
                clearInterval(x);
                this.spinnerValue = 0;
                this.refreshPatients();
            }
        }, 1000);
    }

    refreshPatients(): void {
        this.syncService.get('/patient/').subscribe((res) => {
            console.log("res is ", res);
            this.patients = res;
            this.startTimer();
        });
    }

    ngOnInit(): void {
        this.syncService.get('/hospital/').subscribe((res) => {
            console.log("res is ", res);
            this.hospitals = res;
        });

        this.refreshPatients();
    }

    createPatient(event: any): void {
        event.stopPropagation();
        let dialogRef = this.dialog.open(AddPatientComponent, {
            width: '600px',
            disableClose: true
        });

        dialogRef.afterClosed().subscribe(result => {
            if(result) {
                setTimeout(() => {
                    this.refreshPatients();
                }, 2000);
            }
        });
    }

}
