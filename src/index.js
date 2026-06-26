const express = require('express');
const { pool, redisClient, connectServices } = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get('/health', async (req, res) => {
  try {
    // Check DB
    await pool.query('SELECT 1');
    // Check Redis
    await redisClient.ping();
    
    res.status(200).json({ status: 'ok', message: 'All services healthy' });
  } catch (error) {
    res.status(500).json({ status: 'error', error: error.message });
  }
});

app.get('/api/data', async (req, res) => {
  res.status(200).json({ data: ['item1', 'item2'] });
});

if (require.main === module) {
  connectServices().then(() => {
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  });
}

module.exports = app;
