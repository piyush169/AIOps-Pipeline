const express = require("express");
const { pool, redisClient, connectServices } = require("./db");

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: "1mb" }));

// In-memory store (simulates DB for testability without requiring live Postgres)
let users = [
  { id: 1, name: "Alice Johnson", email: "alice@example.com" },
  { id: 2, name: "Bob Smith", email: "bob@example.com" },
  { id: 3, name: "Charlie Brown", email: "charlie@example.com" },
];
let nextId = 4;

// Email validation helper
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// Health check
app.get("/health", async (req, res) => {
  try {
    await pool.query("SELECT 1");
    await redisClient.ping();
    res.status(200).json({ status: "ok", message: "All services healthy" });
  } catch (error) {
    res.status(500).json({ status: "error", error: error.message });
  }
});

// Data endpoint
app.get("/api/data", (req, res) => {
  res.status(200).json({ data: ["item1", "item2"] });
});

// Config endpoint
app.get("/api/config", (req, res) => {
  res.status(200).json({
    version: "1.0.0",
    environment: process.env.NODE_ENV || "development",
    uptime: process.uptime(),
  });
});

// GET all users
app.get("/api/users", (req, res) => {
  res.status(200).json({ users });
});

// GET user by id
app.get("/api/users/:id", (req, res) => {
  const id = parseInt(req.params.id, 10);
  const user = users.find((u) => u.id === id);
  if (!user) {
    return res.status(404).json({ error: "User not found" });
  }
  res.status(200).json({ user });
});

// POST create user
app.post("/api/users", (req, res) => {
  const { name, email } = req.body;

  if (!name) {
    return res.status(400).json({ error: "Name is required" });
  }
  if (!email) {
    return res.status(400).json({ error: "Email is required" });
  }
  if (!isValidEmail(email)) {
    return res.status(400).json({ error: "Invalid email format" });
  }

  const newUser = { id: nextId++, name, email };
  users.push(newUser);
  res.status(201).json({ user: newUser });
});

// DELETE user by id
app.delete("/api/users/:id", (req, res) => {
  const id = parseInt(req.params.id, 10);
  const index = users.findIndex((u) => u.id === id);
  if (index === -1) {
    return res.status(404).json({ error: "User not found" });
  }
  users.splice(index, 1);
  res.status(200).json({ message: "User deleted successfully" });
});

// 404 handler for unknown routes
app.use((req, res) => {
  res.status(404).json({ error: "Route not found" });
});

// Start server only when run directly
if (require.main === module) {
  connectServices().then(() => {
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  });
}

module.exports = app;
