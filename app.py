from flask import Flask, render_template, request, jsonify, session
import subprocess
from jira import JIRA
import os
import tempfile

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change this!

# Jira config
JIRA_URL = "https://joelrtharakanin.atlassian.net"
JIRA_EMAIL = "joelrtharakan.in@gmail.com"
JIRA_API_TOKEN = "REMOVED_API_TOKEN"
JIRA_PROJECT_KEY = "MFLP"

# Connect to Jira
jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# Allowed file extensions for upload (basic safety)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def query_ollama(prompt):
    try:
        process = subprocess.Popen(
            ["ollama", "run", "llama3.2"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(prompt)
        if process.returncode != 0:
            print("Ollama error:", stderr)
            return "Sorry, I am having trouble answering right now."
        return stdout.strip()
    except Exception as e:
        print(f"Exception querying Ollama: {e}")
        return "Sorry, I am having trouble answering right now."


def create_jira_ticket(summary, description, name, email, attachment_path=None, attachment_filename=None):
    full_description = f"""
Reported by: {name}
Email: {email}

Issue Summary:
{summary}

Details:
{description}
"""
    issue_dict = {
        'project': {'key': JIRA_PROJECT_KEY},
        'summary': f"{summary} (from {name})",
        'description': full_description,
        'issuetype': {'name': 'Task'}
    }
    new_issue = jira.create_issue(fields=issue_dict)

    # Attach file if provided
    if attachment_path and attachment_filename:
        try:
            with open(attachment_path, 'rb') as f:
                jira.add_attachment(issue=new_issue, attachment=f, filename=attachment_filename)
        except Exception as e:
            print(f"Failed to attach file to Jira ticket: {e}")
            # You can handle failure or notify user if needed

    return new_issue.key


@app.route('/')
def index():
    session.clear()  # reset conversation session on homepage load
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True)
        user_msg = data.get('message', '').strip()
        user_info = data.get('user', {})

        if 'ticket_data' not in session:
            session['ticket_data'] = {}

        ticket_data = session['ticket_data']
        issue_keywords = ["ticket", "issue", "problem", "help", "crash", "error", "fail", "bug"]

        # Save name/email from user info if available and not already saved
        if 'name' not in ticket_data and user_info.get('name'):
            ticket_data['name'] = user_info['name']
        if 'email' not in ticket_data and user_info.get('email'):
            ticket_data['email'] = user_info['email']
        session['ticket_data'] = ticket_data

        # Track if waiting for file upload
        if session.get('awaiting_file'):
            return jsonify(reply="Please upload a file before continuing or type 'skip' to continue without a file.")

        if 'creating_ticket' not in session:
            # Detect issue keywords and start ticket creation immediately
            if any(word in user_msg.lower() for word in issue_keywords):
                session['creating_ticket'] = True
                reply = "I see you have an issue. Let's create a support ticket. Please provide a short summary of your issue."
                return jsonify(reply=reply)

            # Else, normal AI response
            reply = query_ollama(user_msg)
            return jsonify(reply=reply)

        else:
            # Step 1: Collect summary
            if 'summary' not in ticket_data:
                ticket_data['summary'] = user_msg
                session['ticket_data'] = ticket_data
                return jsonify(reply="Got it. Please describe the issue in more detail.")

            # Step 2: Collect description and then ask for file upload
            elif 'description' not in ticket_data:
                ticket_data['description'] = user_msg
                session['ticket_data'] = ticket_data
                session['awaiting_file'] = True
                return jsonify(reply="Thank you! Please upload a photo or file as proof (optional). You can also type 'skip' to continue without uploading.")

            # We shouldn't get here because file upload handled separately
            else:
                return jsonify(reply="Waiting for your file upload or type 'skip' to continue.")

    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify(reply="⚠️ Something went wrong. Please try again.")


@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify(success=False, message="No file part in request")

        file = request.files['file']
        if file.filename == '':
            return jsonify(success=False, message="No file selected")

        if file and allowed_file(file.filename):
            # Save file temporarily
            tmp_dir = tempfile.gettempdir()
            temp_path = os.path.join(tmp_dir, file.filename)
            file.save(temp_path)

            # Save file info in session for attaching later
            ticket_data = session.get('ticket_data', {})
            ticket_data['attachment_path'] = temp_path
            ticket_data['attachment_filename'] = file.filename
            session['ticket_data'] = ticket_data

            # Now create Jira ticket with attachment
            ticket_key = create_jira_ticket(
                summary=ticket_data.get('summary', 'No Summary'),
                description=ticket_data.get('description', 'No Description'),
                name=ticket_data.get('name', 'Unknown'),
                email=ticket_data.get('email', 'Not provided'),
                attachment_path=temp_path,
                attachment_filename=file.filename
            )

            # Clear session flags
            session.pop('creating_ticket', None)
            session.pop('ticket_data', None)
            session.pop('awaiting_file', None)

            # Optionally delete temp file after upload
            try:
                os.remove(temp_path)
            except:
                pass

            return jsonify(success=True, message=f"✅ Your ticket has been created successfully with ID: {ticket_key}")

        else:
            return jsonify(success=False, message="Invalid file type. Allowed: png, jpg, jpeg, gif, pdf.")

    except Exception as e:
        print(f"Error in /upload: {e}")
        return jsonify(success=False, message="An error occurred during file upload.")


@app.route('/skip-upload', methods=['POST'])
def skip_upload():
    try:
        ticket_data = session.get('ticket_data', {})
        ticket_key = create_jira_ticket(
            summary=ticket_data.get('summary', 'No Summary'),
            description=ticket_data.get('description', 'No Description'),
            name=ticket_data.get('name', 'Unknown'),
            email=ticket_data.get('email', 'Not provided'),
        )
        session.pop('creating_ticket', None)
        session.pop('ticket_data', None)
        session.pop('awaiting_file', None)
        return jsonify(success=True, message=f"✅ Your ticket has been created successfully with ID: {ticket_key}")
    except Exception as e:
        print(f"Error in /skip-upload: {e}")
        return jsonify(success=False, message="Failed to create ticket on skipping upload.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)