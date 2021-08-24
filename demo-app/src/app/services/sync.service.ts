import { environment } from './../../environments/environment';

import { ErrorHandler, Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators'
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';



const SERVER_URL = environment.serverUrl;

@Injectable()
export class SyncService {

    constructor(
        private http: HttpClient,
    ) { }

    private getHeaders(headers?: any) {
        return new HttpHeaders({
            ...headers,
            'x-tenant-id': location.hostname
        })
    }

    private handleError(error: HttpErrorResponse) {
        console.log("error is ", error);
        const err_msg = "err_msg" in error.error ? error.error.err_msg : error.message;
        alert(
            `An unexpected error occurred ${error.status}. Error message: ${err_msg}`
        );
        return throwError(error);
    }

    get<T>(endpoint: string, params?: any, headers?: any): Observable<T> {
        console.log("server url is ", SERVER_URL);
        return this.http.get<T>(
            SERVER_URL + endpoint,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        }).pipe(catchError(this.handleError));
    }

    post(endpoint: string, data: any, params?: any, headers?: any): Observable<any> { // POST
        return this.http.post(
            SERVER_URL + endpoint, data,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        }).pipe(catchError(this.handleError));
    }

    put(endpoint: string, data: any, params?: any, headers?: any): Observable<any> { // PUT
        return this.http.put(
            SERVER_URL + endpoint, data, {
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        }).pipe(catchError(this.handleError));
    }

    delete(endpoint: string, id: number, headers?: any): Observable<any> { // DELETE
        return this.http.delete(
            SERVER_URL + endpoint,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json'
        }).pipe(catchError(this.handleError));
    }

}
