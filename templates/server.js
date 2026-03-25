const express = require("express");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const app = express();
const upload = multer({ dest: "uploads/" });

let recentFiles = []; 

app.use(express.static("public")); 

app.post("/upload", upload.single("file"), (req, res) => {
  if (!req.file) return res.status(400).send("No file uploaded.");
  const fileMeta = {
    originalName: req.file.originalname,
    path: req.file.path,
    date: new Date().toISOString(),
  };
  
  recentFiles.unshift(fileMeta);
  if (recentFiles.length > 12) recentFiles.pop();
  res.redirect("/main"); 
});

app.get("/recent.json", (req, res) => {
  res.json(recentFiles);
});

app.listen(3000, () => console.log("Server running on http://localhost:3000"));