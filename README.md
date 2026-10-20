# EWB Internship Backend Assignment - Student Portal

This is my backend submission for the EWB internship project assignment. I built a Student Management API that includes full CRUD capabilities and an optional local AI assistant using FastAPI, SQLite, and Ollama.

## Project Features
- **Single File Setup:** To keep things straightforward and fast, the entire backend setup (database connection, models, schemas, and endpoints) is written within a single `main.py` file.
- **Full CRUD Endpoints:** Supports registering a new student, viewing all students (with course filters), updating details, and removing records.
- **Ollama AI Integration:** Built a special endpoint that grabs the current database information safely and uses the local `llama3.2:1b` model to answer natural-language questions about our students.

## How to Setup and Run

1. Open your terminal inside the project directory and create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the environment:
   - On Windows: `venv\Scripts\activate`
   - On Mac/Linux: `source venv/bin/activate`

3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

4. Make sure your local Ollama app is open and running the model in the background:
   ```bash
   ollama run llama3.2:1b
   ```

5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```

## Testing My Endpoints

Once the application starts, you can visit the local browser dashboard to test my implementation:
- **Swagger Docs Link:** http://localhost:8000/docs

From there, you can add mock records using the POST method and try out the AI query tool by asking questions like: *"How many students are enrolled in total?"*
