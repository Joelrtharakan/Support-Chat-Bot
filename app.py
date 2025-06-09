from jira import JIRA
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Your Jira details
JIRA_URL = "https://joelrtharakanin.atlassian.net"  # Your Jira URL
JIRA_EMAIL = "joelrtharakan.in@gmail.com"  # Your Jira email
JIRA_API_TOKEN = "YOUR_JIRA_API_TOKEN"  # Replace with your Jira API token

# Connect to Jira
jira = JIRA(JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# Project Key for Jira
PROJECT_KEY = "MFLP"  # Your Jira Project Key

# Define conversation steps
conversation_steps = {
    1: "Welcome to our support chatbot! How can I help you today?",
    2: "Can you please provide a summary of your issue?",
    3: "Can you please describe the issue in more detail?",
    4: "Thank you! We're creating your ticket now..."
}

user_data = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form['message']
    step = int(request.form['step'])
    response = ""

    if step == 1:
        user_data['initial_query'] = user_input
        response = conversation_steps[2]
    elif step == 2:
        user_data['summary'] = user_input
        response = conversation_steps[3]
    elif step == 3:
        user_data['description'] = user_input
        response = conversation_steps[4]
        step += 1
    elif step == 4:
        # Prepare the data for ticket creation
        ticket_title = user_data.get('summary', 'No title provided')
        ticket_description = user_data.get('description', 'No description provided')

        try:
            # Create an issue in Jira
            new_issue = jira.create_issue(
                project=PROJECT_KEY,
                summary=ticket_title,
                description=ticket_description,
                issuetype={'name': 'Task'}  # Make sure the issue type is correct
            )

            response_message = f"✅ Your ticket has been created successfully! Ticket ID: {new_issue.key}"
        except Exception as e:
            response_message = f"❌ Error: {str(e)}"
            
        return jsonify({'response': response_message, 'next_step': None})

    return jsonify({'response': response, 'next_step': step + 1})

if __name__ == '__main__':
    app.run(debug=True)
