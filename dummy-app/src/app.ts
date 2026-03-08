import express, { Request, Response, NextFunction } from 'express';
import winston from 'winston';
import { metrics } from '@opentelemetry/api';

const app = express();
app.use(express.json());

const logger = winston.createLogger({
    level: 'info',
    format: winston.format.json(),
    defaultMeta: { service: 'node-typescript-app' },
    transports: [
        new winston.transports.Console()
    ]
});

// Setup Custom Metrics
const meter = metrics.getMeter('node-typescript-app-meter');

const requestCounter = meter.createCounter('http.server.requests.total', {
    description: 'Total number of HTTP requests',
});

const activeRequestsGauge = meter.createUpDownCounter('http.server.requests.active', {
    description: 'Number of active HTTP requests',
});

const requestDurationHistogram = meter.createHistogram('http.server.request.duration', {
    description: 'Duration of HTTP requests in milliseconds',
    unit: 'ms',
});

// Middleware to track metrics
app.use((req: Request, res: Response, next: NextFunction) => {
    const startTime = Date.now();
    activeRequestsGauge.add(1);

    res.on('finish', () => {
        const duration = Date.now() - startTime;
        const labels = {
            method: req.method,
            route: req.route ? req.route.path : req.path,
            status_code: res.statusCode.toString(),
        };

        activeRequestsGauge.add(-1);
        requestCounter.add(1, labels);
        requestDurationHistogram.record(duration, labels);
    });

    next();
});

// 1. Success - Simple Object
app.get('/', (req: Request, res: Response) => {
    logger.info('Handling request for root endpoint');
    res.status(200).json({ status: 'ok', message: 'Welcome to the dummy API!' });
});

// 2. Success - Data List
app.get('/users', (req: Request, res: Response) => {
    logger.info('Fetching list of users');
    res.status(200).json({
        data: [
            { id: 1, name: 'Alice', role: 'admin' },
            { id: 2, name: 'Bob', role: 'user' },
        ],
        meta: { total: 2 }
    });
});

// 3. Simulated Slowness (Success)
app.get('/slow', async (req: Request, res: Response) => {
    logger.warn('Processing an unusually slow request');
    await new Promise(resolve => setTimeout(resolve, 800));
    res.status(200).json({ status: 'success', message: 'This took a while' });
});

// 4. Client Error (400 Bad Request)
app.post('/users', (req: Request, res: Response): void => {
    if (!req.body || !req.body.name) {
        logger.warn('Client provided invalid user payload', { body: req.body });
        res.status(400).json({ error: 'Bad Request', details: 'name is required' });
        return;
    }
    logger.info('Created new user', { user: req.body });
    res.status(201).json({ status: 'created', user: req.body });
});

// 5. Client Error (401 Unauthorized)
app.get('/admin', (req: Request, res: Response) => {
    logger.warn('Unauthorized access attempt to admin panel');
    res.status(401).json({ error: 'Unauthorized', message: 'Missing authentication token' });
});

// 6. Client Error (404 Not Found)
app.get('/missing-data', (req: Request, res: Response) => {
    logger.warn('Attempted to access non-existent resource: /missing-data');
    res.status(404).json({ error: 'Not Found', message: 'The requested resource does not exist' });
});

// 7. Server Error (500 Internal Server Error)
app.get('/error', (req: Request, res: Response) => {
    try {
        throw new Error('Database connection failed');
    } catch (err: unknown) {
        logger.error('Unhandled Exception in /error endpoint', {
            error: err instanceof Error ? err.message : String(err),
            stack: err instanceof Error ? err.stack : undefined
        });
        res.status(500).json({ error: 'Internal Server Error', message: err instanceof Error ? err.message : String(err) });
    }
});

// 8. Server Error (502 Bad Gateway) - Simulating external service failure
app.get('/external', (req: Request, res: Response) => {
    logger.error('Failed to communicate with upstream external service');
    res.status(502).json({ error: 'Bad Gateway', message: 'Upstream service is unreachable' });
});

app.listen(3000, () => logger.info("Server started on port 3000"));
