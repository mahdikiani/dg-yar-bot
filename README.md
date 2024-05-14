# Django Docker Boilerplate
This boilerplate provides a comprehensive setup for a Django application, utilizing Docker and Docker Compose for containerization, Traefik for reverse proxy, and including Celery for asynchronous task management with Redis. PostgreSQL is used as the database. This setup is designed for development and production environments, ensuring easy scalability and deployment.

## Features
- Django 5.x: Modern Django framework setup.
- Docker and Docker Compose: Containerization of all components.
- Traefik: Easy reverse proxy and SSL termination.
- Celery with Redis: Asynchronous task processing.
- PostgreSQL: Robust and scalable database.
- Open Source: MIT Licensed.

## Prerequisites
- Docker
- Docker Compose

## Quick Start
1. Clone the repository:
```bash
git clone https://github.com/mahdikiani/DjangoLaunchpad.git
```

2. Navigate into the project directory:
```bash
cd DjangoLaunchpad
```

3. Initialize and start the containers:
```bash
docker-compose up --build
```

4. Access the application at http://localhost or configure Traefik for custom domain access.


## Configuration
### Environment Variables
Create a `.env` file in the root directory from `sample.env` and update it with your settings:

```bash
cp sample.env .env
```

### Traefik
Traefik is configured in `docker-compose.yml`. Adjust the settings according to your domain and SSL requirements.

## Contributing
Contributions are welcome! Please read the contributing guide to learn how to propose bugfixes, improvements, and new features.

## License
This project is open source and available under the [MIT License](https://github.com/mahdikiani/DjangoLaunchpad/blob/main/LICENSE).

## Acknowledgments
This boilerplate is inspired by best practices and several community projects. Your contributions and suggestions are welcome!

