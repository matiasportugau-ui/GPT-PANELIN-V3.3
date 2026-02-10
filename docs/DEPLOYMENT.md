# Deployment Guide

## Prerequisites

- Node.js 16.x or higher
- npm or yarn
- Docker (optional, for containerized deployment)

## Development Deployment

1. Clone and setup:
```bash
git clone https://github.com/matiasportugau-ui/GPT-PANELIN-V3.2.git
cd GPT-PANELIN-V3.2
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Production Deployment

### Option 1: Traditional Build

1. Build the application:
```bash
npm run build
```

2. The build output will be in the `dist/` directory

3. Serve using any static file server:
```bash
npx serve -s dist
```

### Option 2: Docker Deployment

1. Build the Docker image:
```bash
docker build -t gpt-panelin-v3.2 .
```

2. Run the container:
```bash
docker run -p 80:80 gpt-panelin-v3.2
```

### Option 3: Docker Compose

```bash
docker-compose up -d
```

## Deployment Platforms

### Vercel

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

### Netlify

1. Install Netlify CLI:
```bash
npm i -g netlify-cli
```

2. Deploy:
```bash
netlify deploy --prod
```

### AWS (S3 + CloudFront)

1. Build the application:
```bash
npm run build
```

2. Upload to S3:
```bash
aws s3 sync dist/ s3://your-bucket-name
```

3. Configure CloudFront distribution pointing to the S3 bucket

## Environment Variables

Required environment variables for production:

- `VITE_API_BASE_URL`: API endpoint URL
- `VITE_OPENAI_API_KEY`: OpenAI API key (if using direct integration)
- `VITE_OPENAI_MODEL`: GPT model to use (default: gpt-3.5-turbo)

## Post-Deployment Checklist

- [ ] Verify all environment variables are set
- [ ] Test the application functionality
- [ ] Check API connectivity
- [ ] Verify SSL/TLS certificate (for HTTPS)
- [ ] Configure CORS if needed
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Test error handling

## Troubleshooting

### Build Failures

- Ensure Node.js version is 16.x or higher
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check for syntax errors: `npm run lint`

### API Connection Issues

- Verify API URL is correct
- Check CORS configuration
- Validate API keys

### Docker Issues

- Ensure Docker daemon is running
- Check port availability
- Verify nginx configuration

## Monitoring

Consider implementing:

- Application Performance Monitoring (APM)
- Error tracking (e.g., Sentry)
- Log aggregation
- Uptime monitoring
- Analytics

## Scaling

For high-traffic scenarios:

1. Use a CDN for static assets
2. Implement caching strategies
3. Use load balancers for multiple instances
4. Consider serverless deployments
5. Optimize bundle size and lazy loading
