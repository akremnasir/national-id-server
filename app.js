const express = require("express");
const multer = require("multer");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 5000;

// Configure CORS
const allowedOrigins = [
  "https://id-for-you.netlify.app",  // Production frontend
  "http://localhost:3000"           // Local development
];

const corsOptions = {
  origin: function (origin, callback) {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);
    
    if (allowedOrigins.indexOf(origin) === -1) {
      const msg = `CORS policy: ${origin} not allowed`;
      return callback(new Error(msg), false);
    }
    return callback(null, true);
  },
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
  exposedHeaders: ['Content-Disposition']
};

app.use(cors(corsOptions));

// Handle preflight requests
app.options('*', cors(corsOptions));

// Setup Multer for PDF upload
const upload = multer({ 
  dest: "uploads/",
  limits: {
    fileSize: 5 * 1024 * 1024 // 5MB file size limit
  }
});

// Ensure directories exist
const ensureDirectories = () => {
  const dirs = ['uploads', 'generated'];
  dirs.forEach(dir => {
    if (!fs.existsSync(dir)){
      fs.mkdirSync(dir);
    }
  });
};

ensureDirectories();

// Error handling middleware
app.use((err, req, res, next) => {
  if (err.message.includes('CORS policy')) {
    return res.status(403).json({ error: err.message });
  }
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ error: err.message });
  }
  next(err);
});

// Main route for ID generation
app.post("/generate-id", upload.single("file"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }

  const filePath = req.file.path;
  const originalName = req.file.originalname;
  const template = req.body.template || "Template 1";

  const python = spawn("python3", ["generate_id.py", filePath, originalName, template]);

  let outputName = "";
  let errorOutput = "";

  python.stdout.on("data", (data) => {
    outputName += data.toString().trim();
  });

  python.stderr.on("data", (data) => {
    errorOutput += data.toString();
    console.error(`Python Error: ${data}`);
  });

  python.on("close", (code) => {
    // Clean up uploaded file
    fs.unlink(filePath, (err) => {
      if (err) console.error("Error deleting uploaded file:", err);
    });

    if (code !== 0 || !outputName) {
      console.error("Python script failed:", { code, errorOutput });
      return res.status(500).json({ 
        error: "Failed to generate ID",
        details: errorOutput || "Unknown error occurred"
      });
    }

    const imagePath = path.join(__dirname, "generated", outputName);

    if (!fs.existsSync(imagePath)) {
      console.error("Generated image not found:", imagePath);
      return res.status(500).json({ error: "Generated image not found" });
    }

    res.sendFile(imagePath, (err) => {
      if (err) {
        console.error("Error sending file:", err);
        return res.status(500).json({ error: "Failed to send generated image" });
      }

      // Clean up generated image after sending
      fs.unlink(imagePath, (err) => {
        if (err) console.error("Error deleting generated image:", err);
      });
    });
  });
});

// Health check endpoint
app.get("/health", (req, res) => {
  res.status(200).json({ status: "healthy" });
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`Allowed origins: ${allowedOrigins.join(", ")}`);
});