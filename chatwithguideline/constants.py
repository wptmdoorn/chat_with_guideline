from datetime import datetime
import json

welcome_message = '''
Hello! Welcome to "Chat with your medical guideline"! 
I have direct access to all the content of various medical guidelines. 
Please pick a guideline from the left side of the screen and ask me a question about it. As an alternative, 
you can explore by picking a random guideline and asking me a question about it.
'''

new_guideline_message = '''
I now have direct access to all the content of <b>{label}</b>. 
Moreover, you instructed me to be talk with you on a <b>{level}</b> level of expertise and with 
a <b>{creativity}</b> level of creativity.
How can I help you? Please ask whatever you want to know.
'''

llm_levels = ['Laymen', 'Intermediate', 'Advanced', 'Expert']
llm_creativity = {'Very focused': 0, 'Focused': 0.25,
                  'Balanced': 0.5, 'Creative': 0.75, 'Very creative': 1}


def format_bot_message(text: str) -> dict:
    stamp = datetime.utcnow().strftime('%X')

    return {
        "name": 'Bot',
        "text": text,
        "avatar": 'https://robohash.org/assistant?bgset=bg2',
        "stamp": stamp
    }


def list_guidelines(with_specialty=False) -> dict:
    with open('embeddings/metadata.json', 'r') as f:
        if with_specialty:
            return json.load(f)
        else:
            return {x['dir'].strip(): x['title'].strip() for x in json.load(f)}
