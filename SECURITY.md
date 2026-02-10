# Security Policy

## Supported Versions

Currently supported versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 3.2.x   | :white_check_mark: |
| < 3.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in GPT PANELIN V3.2, please follow these steps:

1. **Do NOT** open a public issue
2. Email the maintainers at security@example.com with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Security Best Practices

When deploying GPT PANELIN V3.2:

1. Never commit `.env` files with real credentials
2. Use environment variables for sensitive data
3. Keep dependencies up to date
4. Use HTTPS in production
5. Implement rate limiting for API endpoints
6. Regularly rotate API keys and secrets
7. Enable CORS only for trusted domains
8. Use strong session secrets

## Known Security Considerations

- Always configure API keys through environment variables
- Implement proper authentication before deploying to production
- Review and limit API rate limits based on your use case
