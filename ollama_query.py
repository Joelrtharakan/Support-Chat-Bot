import requests

def query_ollama(prompt):
    url = "http://localhost:11434/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "llama3",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        # Extract the reply text depending on API response format
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("Error querying Ollama:", e)
        return "⚠️ Unable to fetch response from AI."