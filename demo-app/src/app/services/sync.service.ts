import { environment } from './../../environments/environment';

import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';



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

    get<T>(endpoint: string, params?: any, headers?: any): Observable<T> {
        console.log("server url is ", SERVER_URL);
        return this.http.get<T>(
            SERVER_URL + endpoint,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        });
    }

    post(endpoint: string, data: any, params?: any, headers?: any): Observable<any> { // POST
        return this.http.post(
            SERVER_URL + endpoint, data,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        });
    }

    put(endpoint: string, data: any, params?: any, headers?: any): Observable<any> { // PUT
        return this.http.put(
            SERVER_URL + endpoint, data, {
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json',
            params
        });
    }

    delete(endpoint: string, id: number, headers?: any): Observable<any> { // DELETE
        return this.http.delete(
            SERVER_URL + endpoint,{
            headers: this.getHeaders(headers),
            observe: 'body',
            responseType: 'json'
        });
    }

}
