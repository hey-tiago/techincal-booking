# Technician Booking System - Backend

This backend application is built using FastAPI and Tortoise ORM with SQLite. It manages technician bookings by allowing users to list, retrieve, delete, and schedule appointments. Additionally, it includes a natural language “chat” endpoint to process booking instructions from the console.

Setup Instructions

1. Clone the Repository

Clone the repository to your local machine:

```

git clone <repository_url>
cd <repository_directory>

```

2. Create a Python Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

```

python -m venv venv
source venv/bin/activate

```

3. Install Dependencies

All dependencies are listed in the requirements.txt file. Install them with:

```
pip install -r requirements.txt
```

4. Run the Backend Server

Copy the .env.example file to .env and add your OpenAI API key.

```

cp .env.example .env

```

To start the FastAPI server with auto-reload enabled, run:

```

uvicorn main:app –reload

```

The API will be available at http://localhost:8000.

5. (Optional) Run the Console Interface

If you prefer to interact with the system via a command-line console, run:

```

python main.py console

```

Then, follow the prompts to enter natural language booking instructions.

API Endpoints
• GET /bookings: List all bookings.
• GET /bookings/{booking_id}: Retrieve a booking by its ID.
• DELETE /bookings/{booking_id}: Delete a booking by its ID.
• POST /bookings: Schedule a new booking.
Payload example:

```

{
“technician_name”: “John Doe”,
“service”: “Gardener”,
“booking_datetime”: “2022-10-20T17:00:00”
}

```

    •	POST /chat: Process a natural language message.

Payload example:

```

{
“message”: “I want to book a gardener for tomorrow at 5:00pm”
}

```

Additional Notes
• Database: The application uses SQLite. The database file (bookings.db) will be automatically created in the project root.
• CORS: The backend is configured to allow all origins to facilitate development with the frontend. Adjust CORS settings appropriately for production.
• Error Handling: The API provides meaningful error messages for scenarios like booking conflicts or invalid IDs.

Troubleshooting
• Virtual Environment: Ensure the virtual environment is activated before installing dependencies or running the server.
• Database Issues: Check the console logs for errors related to database initialization or connection.

License

[Include license information if applicable]

```

```
