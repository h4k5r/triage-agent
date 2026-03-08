import http from 'k6/http';
import { check, sleep } from 'k6';
import { Options } from 'k6/options';

// Configure the load test: Ramp up to 50 users over 10s, hold for 20s, ramp down over 10s.
export const options: Options = {
    stages: [
        { duration: '10s', target: 50 },
        { duration: '20s', target: 50 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<1500'], // 95% of requests must complete below 1.5s
    },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:3000';

export default function () {
    // Scenario 1: Fetch users (Successful 200 OK)
    const resUsers = http.get(`${BASE_URL}/users`);
    check(resUsers, {
        'users status is 200': (r) => r.status === 200,
    });

    // Scenario 2: Missing data (404 Not Found)
    const resMissing = http.get(`${BASE_URL}/missing-data`);
    check(resMissing, {
        'missing data status is 404': (r) => r.status === 404,
    });

    // Scenario 3: Trigger slow endpoint occasionally to populate histogram differently
    if (Math.random() < 0.2) {
        const resSlow = http.get(`${BASE_URL}/slow`);
        check(resSlow, {
            'slow endpoint status is 200': (r) => r.status === 200,
        });
    }

    // Scenario 4: Trigger an error occasionally to populate 500 status codes
    if (Math.random() < 0.1) {
        const resError = http.get(`${BASE_URL}/error`);
        check(resError, {
            'error endpoint status is 500': (r) => r.status === 500,
        });
    }

    // Short sleep to simulate real user think time between interactions
    sleep(1);
}
