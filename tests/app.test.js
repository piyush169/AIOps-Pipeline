const request = require('supertest');
const app = require('../src/index');

describe('API Endpoints', () => {
  describe('GET /api/data', () => {
    it('should return 200 OK', async () => {
      const res = await request(app).get('/api/data');
      expect(res.statusCode).toEqual(200);
    });

    it('should return a JSON response with data array', async () => {
      const res = await request(app).get('/api/data');
      expect(res.body).toHaveProperty('data');
      expect(Array.isArray(res.body.data)).toBe(true);
    });

    it('should return a non-empty data array', async () => {
      const res = await request(app).get('/api/data');
      expect(res.body.data.length).toBeGreaterThan(0);
    });

    it('should contain expected items', async () => {
      const res = await request(app).get('/api/data');
      expect(res.body.data).toContain('item1');
      expect(res.body.data).toContain('item2');
    });

    it('should have correct content-type header', async () => {
      const res = await request(app).get('/api/data');
      expect(res.headers['content-type']).toMatch(/json/);
    });
  });

  describe('GET /health', () => {
    it('should return health status object', async () => {
      const res = await request(app).get('/health');
      expect(res.body).toHaveProperty('status');
    });
  });

  describe('GET /api/users', () => {
    it('should return 200 OK', async () => {
      const res = await request(app).get('/api/users');
      expect(res.statusCode).toEqual(200);
    });

    it('should return users array', async () => {
      const res = await request(app).get('/api/users');
      expect(res.body).toHaveProperty('users');
      expect(Array.isArray(res.body.users)).toBe(true);
    });

    it('should return users with id and name fields', async () => {
      const res = await request(app).get('/api/users');
      res.body.users.forEach(user => {
        expect(user).toHaveProperty('id');
        expect(user).toHaveProperty('name');
        expect(user).toHaveProperty('email');
      });
    });
  });

  describe('POST /api/users', () => {
    it('should create a new user and return 201', async () => {
      const newUser = { name: 'Test User', email: 'test@example.com' };
      const res = await request(app).post('/api/users').send(newUser);
      expect(res.statusCode).toEqual(201);
      expect(res.body).toHaveProperty('user');
      expect(res.body.user.name).toEqual('Test User');
    });

    it('should return 400 if name is missing', async () => {
      const res = await request(app).post('/api/users').send({ email: 'test@example.com' });
      expect(res.statusCode).toEqual(400);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 400 if email is missing', async () => {
      const res = await request(app).post('/api/users').send({ name: 'Test User' });
      expect(res.statusCode).toEqual(400);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 400 if email format is invalid', async () => {
      const res = await request(app).post('/api/users').send({ name: 'Test', email: 'not-an-email' });
      expect(res.statusCode).toEqual(400);
    });
  });

  describe('GET /api/users/:id', () => {
    it('should return a specific user by id', async () => {
      const res = await request(app).get('/api/users/1');
      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('user');
      expect(res.body.user.id).toEqual(1);
    });

    it('should return 404 for non-existent user', async () => {
      const res = await request(app).get('/api/users/99999');
      expect(res.statusCode).toEqual(404);
    });
  });

  describe('DELETE /api/users/:id', () => {
    it('should delete a user and return 200', async () => {
      const res = await request(app).delete('/api/users/1');
      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('message');
    });

    it('should return 404 when deleting non-existent user', async () => {
      const res = await request(app).delete('/api/users/99999');
      expect(res.statusCode).toEqual(404);
    });
  });

  describe('GET /api/config', () => {
    it('should return application configuration', async () => {
      const res = await request(app).get('/api/config');
      expect(res.statusCode).toEqual(200);
      expect(res.body).toHaveProperty('version');
      expect(res.body).toHaveProperty('environment');
    });
  });
});

describe('Input Validation', () => {
  it('should reject payloads larger than 1MB', async () => {
    const largePayload = { data: 'x'.repeat(1024 * 1024 + 1) };
    const res = await request(app).post('/api/users').send(largePayload);
    expect(res.statusCode).toBeGreaterThanOrEqual(400);
  });

  it('should handle special characters in query params', async () => {
    const res = await request(app).get('/api/data?filter=<script>alert(1)</script>');
    expect(res.statusCode).not.toEqual(500);
  });
});

describe('Error Handling', () => {
  it('should return 404 for unknown routes', async () => {
    const res = await request(app).get('/api/nonexistent');
    expect(res.statusCode).toEqual(404);
  });

  it('should return proper error format', async () => {
    const res = await request(app).get('/api/nonexistent');
    expect(res.body).toHaveProperty('error');
  });
});
