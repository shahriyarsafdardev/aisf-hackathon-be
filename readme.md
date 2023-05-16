# AISF - HACKATHON - BACKEND

This is the FastAPI Python backend.


## Running the app locally

Create a virtual environment in the project root:

```python -m venv venv```

Activate the virtual environment:

```source venv/bin/activate```

Install the required dependencies:

```pip install -r requirements.txt```

### 4. Run the server

Run the server using the following command:

```uvicorn app:app --host 0.0.0.0 --port 8000 --reload```

The server should now be running at `http://localhost:8000`.

You can run the app locally by running this command in terminal


## Deployment on Heroku

Login to Heroku:

```heroku login```

After successful login, Deploy the app on Heroku:

```git push heroku-aisf master:master```

Wait for the deployment to complete.

The server should now be running at `https://sphere-aisf-hackathon-be.herokuapp.com/`.

