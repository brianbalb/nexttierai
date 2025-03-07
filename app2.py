from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Set up the secret key for sessions
app.secret_key = 'your_secret_key'

# SQLite URI - You can change the database file path (default is "job_projects.db")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///job_projects.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable Flask-SQLAlchemy modification tracking

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define the Project model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(500), nullable=False)
    generated_response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Get API key from environment variable
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("Error: OPENROUTER_API_KEY is not set in the environment.")

# AI response generator function
def generate_job_project(user_input):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {
                "role": "system",
                "content": "You are an AI career coach and creative project generator; specializing in crafting unique, one of a kind, skill-showcasing project tailored to job posting. Your goal is to create a unique project based on the user's input to help them gain real-world experience, build a strong portfolio, and stand out in job applications by generating one custom, actionable project aligned with the key skills in a given job post. Instructions: Analyze the Job Post – Extract key skills, tools, and employer expectations. Generate One Unique Project – The project must directly showcase the role's core competencies, be challenging yet achievable, and align with industry standards. Structure the Response Using These Sections: Job Post Analysis: List extracted keywords, key skills, tools, and employer expectations. Project Idea: Provide a title and brief overview of the project. Project Milestones: Break down the project into five clear steps for structured execution.Project Tools: List the necessary technologies. Project Deliverables: Outline key components the user will complete. Project Presentation Tips: Guide the user on how to showcase their project effectively (portfolio, live demo, technical explanations). Resume Tips: Provide impactful bullet points that incorporate industry-relevant keywords. The AI must ensure consistency in format, eliminate redundancy, and make the instructions concise yet comprehensive to maximize the project's effectiveness in securing job opportunities."
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raises an error for 4xx/5xx responses
        data = response.json()

        if "choices" not in data:
            raise ValueError("Error: Unexpected response format from OpenRouter API.")

        return data['choices'][0]['message']['content']  # Extract relevant content from response
    except requests.exceptions.RequestException as e:
        print("API Request Error:", e)
        return {"error": "Failed to connect to AI service."}
    except ValueError as e:
        print("Response Processing Error:", e)
        return {"error": "Invalid response format from AI service."}

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_input = request.form.get('user_input', '').strip()

        if not user_input:
            return "Error: Input cannot be empty!", 400

        response = generate_job_project(user_input)

        if "error" in response:
            return response["error"], 500  # Handle API errors

        # Store the generated project in SQLite
        new_project = Project(user_input=user_input, generated_response=response)
        db.session.add(new_project)
        db.session.commit()

        session['current_project'] = new_project.id  # Store project ID in session
        return redirect(url_for('display_project', project_id=new_project.id))

    return render_template('index.html')  # Make sure index.html is in the templates folder

@app.route('/project/<int:project_id>', methods=['GET'])
def display_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project.html', project=project)  # Make sure project.html is in the templates folder

if __name__ == '__main__':
    # Initialize database tables (only for the first run)
    with app.app_context():
        db.create_all()

    app.run(debug=True)
