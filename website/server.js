// const express = require("express");
// const path = require("path");

// const app = express();
// const port = 3000;

// // Serve the static HTML file
// app.use(express.static(path.join(__dirname, "public")));

// // Start the server
// app.listen(port, () => {
//   console.log(`✅ Node website is running at http://localhost:${port}`);
// });

// server.js
const http = require("http");
const fs = require("fs");
const path = require("path");

const port = 3000;

const server = http.createServer((req, res) => {
  // Serve index.html for root
  let filePath = req.url === "/" ? "/index.html" : req.url;
  filePath = path.join(__dirname, "public", filePath);

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("404 Not Found");
      return;
    }

    // Serve HTML, CSS, JS files based on extension
    const ext = path.extname(filePath);
    let contentType = "text/html";

    if (ext === ".js") contentType = "application/javascript";
    else if (ext === ".css") contentType = "text/css";
    else if (ext === ".json") contentType = "application/json";

    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
  });
});

server.listen(port, () => {
  console.log(`✅ Node server running at http://localhost:${port}`);
});
