const express = require("express");
const multer = require("multer");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");
const cors = require("cors");

const app = express();
const PORT = process.env.PORT || 5000;

const allowedOrigins = ["http://localhost:3000", "https://id-for-you.netlify.app/"];

app.use(cors({
  origin: function (origin, callback) {
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error("Not allowed by CORS"));
    }
  },
  credentials: true,
  exposedHeaders: ["Content-Disposition"]
}));


// Setup Multer for PDF upload
const upload = multer({ dest: "uploads/" });

// Main route for ID generation
app.post("/generate-id", upload.single("file"), (req, res) => {
  const filePath = req.file.path;
  const originalName = req.file.originalname;
  const template = req.body.template || "Template 1"; // Default template if none is selected

  const python = spawn("python3", ["generate_id.py", filePath, originalName, template]);

  let outputName = "";

  python.stdout.on("data", (data) => {
    outputName += data.toString().trim();
  });

  python.stderr.on("data", (data) => {
    console.error(`stderr: ${data}`);
  });

  python.on("close", (code) => {
    // Clean up uploaded file
    fs.unlink(filePath, () => {});

    if (code !== 0) {
      console.error("Python script exited with code:", code);
      return res.status(500).send("Failed to generate image.");
    }

    const imagePath = path.join(__dirname, "generated", outputName);

    // Log image path before sending
    console.log(`Generated ID image: ${imagePath}`);

    res.sendFile(imagePath, (err) => {
      if (err) {
        console.error("SendFile Error:", err);
      }

      // Clean up generated image
      fs.unlink(imagePath, () => {});
    });
  });
});

app.listen(PORT, () => console.log(`🚀 Server running at http://localhost:${PORT}`));
