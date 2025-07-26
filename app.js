const express = require("express");
const multer = require("multer");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

const app = express();
const PORT = 5000;

// Allow CORS
app.use(require("cors")());

// Upload storage config
const upload = multer({ dest: "uploads/" });

app.post("/generate-id", upload.single("file"), (req, res) => {
  const filePath = req.file.path;
  const originalName = req.file.originalname;
  const template = req.body.template || "Template 1"; // default

  const python = spawn("python3", ["generate_id.py", filePath, originalName, template]);

  let outputName = "";
  python.stdout.on("data", (data) => {
    outputName += data.toString().trim();
  });

  python.stderr.on("data", (data) => {
    console.error(`stderr: ${data}`);
  });

  python.on("close", (code) => {
    fs.unlink(filePath, () => {}); // delete uploaded PDF

    if (code !== 0) {
      return res.status(500).send("Failed to generate image.");
    }

    const imagePath = path.join(__dirname, "generated", outputName);
    res.sendFile(imagePath, (err) => {
      if (err) console.error("SendFile Error:", err);
      fs.unlink(imagePath, () => {}); // cleanup image after sending
    });
  });
});

app.listen(PORT, () => console.log(`Server started on http://localhost:${PORT}`));