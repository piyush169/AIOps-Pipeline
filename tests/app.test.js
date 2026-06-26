const request = require('supertest');
const app = require('../src/index');

describe('API Endpoints', () => {
  it('should return 200 OK for /api/data', async () => {
    const res = await request(app).get('/api/data');
    expect(res.statusCode).toEqual(200);
    expect(res.body).toHaveProperty('data');
    expect(res.body.data.length).toBeGreaterThan(0);
  });
});
