import { createServer } from 'http';

const server = createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Test server working!\n');
});

server.listen(5173, '0.0.0.0', () => {
  console.log('Server running at:');
  console.log('  http://localhost:5173/');
  console.log('  http://127.0.0.1:5173/');
  console.log('  http://192.168.110.187:5173/');
  console.log('  http://192.168.196.88:5173/');
});