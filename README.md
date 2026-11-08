# Koya Clinic Booking API

A clinic appointment booking API and web interface built with FastAPI, SQLAlchemy, and PostgreSQL.

**Author:** Popoola Ibrahim

**Live Application:** https://clinic-booking-api-2lhw.onrender.com

**API Documentation:** https://clinic-booking-api-2lhw.onrender.com/docs

## Project Overview

This project provides a clinic appointment booking system that allows patients to view available appointment slots, book appointments, and receive booking confirmations.

It includes a REST API and a simple web interface. Appointment and booking records are stored in a database to ensure persistence across requests.

## Features

- View available appointment slots.
- Filter appointment slots by healthcare provider.
- Book available appointments.
- Retrieve individual booking details.
- Cancel confirmed bookings.
- Prevent duplicate bookings for the same appointment slot, including concurrent requests.
- Support idempotency keys to prevent duplicate bookings when requests are retried.
- Retrieve bookings by email with cursor-based pagination.
- Limit booking attempts to five per email per minute.
- Protect API endpoints using API key authentication.
- Persist appointment and booking records in PostgreSQL.

## Technology Stack

- **Python** – application language.
- **FastAPI** – API framework.
- **SQLAlchemy** – database ORM.
- **PostgreSQL (Neon)** – production database.
- **SQLite** – local development database.
- **Render** – application hosting.
- **HTML, CSS and JavaScript** – frontend.

## Project Structure

```text
Koya-Clinic-Booking/
├── app/
│   ├── routes/
│   │   ├── bookings.py
│   │   ├── slots.py
│   │   └── web.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── security.py
├── static/
│   └── index.html
├── tests/
├── main.py
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/popsy208/clinic-booking-api.git
cd clinic-booking-api
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
API_KEY=your_private_api_key
DATABASE_URL=sqlite:///./clinic.db
```

For production, configure `DATABASE_URL` with your PostgreSQL connection string and `API_KEY` through your hosting provider's environment-variable settings.

Never commit your `.env` file or expose your private API key.

### 5. Start the application

```powershell
uvicorn main:app --reload
```

The local application will be available at:

- Webpage: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs

## API Authentication

Protected API endpoints require the following HTTP header:

```http
X-API-Key: your_private_api_key
```

Requests with a missing or invalid API key receive `401 Unauthorized`.

The browser-facing webpage communicates with the application through same-origin routes without exposing the private API key in frontend JavaScript.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/reset` | Replace appointment slots and delete existing bookings |
| GET | `/slots` | List appointment slots |
| POST | `/bookings` | Create a booking |
| GET | `/bookings/{id}` | Retrieve a booking |
| GET | `/bookings` | Retrieve bookings by email with pagination |
| DELETE | `/bookings/{id}` | Cancel a booking |

### Create a Booking

`POST /bookings`

Example request:

```json
{
  "slot_id": "s1",
  "name": "Test Patient",
  "email": "patient@example.com"
}
```

An optional `Idempotency-Key` header supports safe retries and prevents duplicate bookings.

### List Bookings

`GET /bookings?email=patient@example.com&limit=10`

The endpoint supports cursor-based pagination using the returned `next_cursor`.

### Cancel a Booking

`DELETE /bookings/{id}`

Cancelling a booking changes its status to `cancelled` and makes the appointment slot available again.

## Webpage Routes

The frontend communicates with the application through:

- `GET /web/slots` – retrieve appointment slots.
- `POST /web/bookings` – submit a booking.

The webpage allows patients to view available appointments, select a slot, enter their details, and receive booking confirmations.

## Database Persistence

The application uses SQLAlchemy to communicate with its database.

- Local development uses SQLite.
- Production uses Neon PostgreSQL.
- Appointment slots and bookings are stored in the database rather than temporary in-memory storage.

This ensures booking information remains available across subsequent requests and application restarts, provided the production database remains available.

## Deployment

The application is deployed on Render and uses Neon PostgreSQL for persistent production storage.

Production environment variables:

- `API_KEY`
- `DATABASE_URL`

The production API and webpage are accessible over HTTPS.

## Important Note

`POST /reset` is a destructive administrative endpoint. It replaces existing appointment slots and deletes all existing bookings. Use it carefully, especially in production.

## Author

**Popoola Ibrahim**

Designed, developed, and deployed by Popoola Ibrahim as part of the Koya Academy Cohort 4 assessment.
