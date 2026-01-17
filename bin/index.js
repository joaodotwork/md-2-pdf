#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Path to the python script
const scriptPath = path.join(__dirname, '../md_to_pdf.py');

// Forward all arguments passed to this script
const args = [scriptPath, ...process.argv.slice(2)];

// Spawn the python process
// We use 'inherit' to preserve colors and output streaming
const pythonProcess = spawn('python3', args, { stdio: 'inherit' });

pythonProcess.on('error', (err) => {
  console.error('Failed to start python process:', err);
  console.error('Make sure python3 is installed and available in your PATH.');
  process.exit(1);
});

pythonProcess.on('close', (code) => {
  process.exit(code);
});
