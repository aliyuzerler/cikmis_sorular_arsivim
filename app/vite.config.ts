import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'

// data/ klasörünü /data yolundan servis eden basit middleware
function serveData() {
  const dataRoot = path.resolve(__dirname, '..', 'data')
  const types: Record<string, string> = {
    '.json': 'application/json',
    '.webp': 'image/webp',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
  }
  return {
    name: 'serve-data',
    configureServer(server: any) {
      server.middlewares.use('/data', (req: any, res: any, next: any) => {
        const rel = decodeURIComponent(req.url?.split('?')[0] ?? '/')
        const file = path.join(dataRoot, rel.replace(/^\//, ''))
        if (file.startsWith(dataRoot) && fs.existsSync(file) && fs.statSync(file).isFile()) {
          res.setHeader('Content-Type', types[path.extname(file)] ?? 'application/octet-stream')
          fs.createReadStream(file).pipe(res)
          return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), serveData()],
})
