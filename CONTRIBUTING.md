# Contributing to AgriAsset

## Development Setup
1. Clone the repository
2. Copy `.env.example` to `.env`
3. Run `docker-compose -f docker-compose.dev.yml up`
4. Run migrations: `python manage.py migrate`

## Code Standards
- Python: Follow PEP 8
- JavaScript/TypeScript: Follow ESLint rules
- Write tests for all new features

## Pull Request Process
1. Create a feature branch from `main`
2. Write tests and documentation
3. Submit PR with a clear description