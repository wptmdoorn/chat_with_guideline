#!/usr/bin/env python3
import json, jsonpickle
import random
from datetime import datetime
from dotenv import load_dotenv
from nicegui import Client, ui, app
from typing import List, Tuple
from uuid import uuid4

from llm import create_llm


load_dotenv()

_levels = ['Laymen', 'Intermediate', 'Advanced', 'Expert']
_creativity = {'Very focused': 0, 'Focused': 0.25, 'Balanced': 0.5, 'Creative': 0.75, 'Very creative': 1}


def list_guidelines(with_specialty=False) -> dict:
    with open('embeddings/metadata.json', 'r') as f:
        if with_specialty:
            return json.load(f)
        else:
            return {x['dir']: x['title'] for x in json.load(f)}


@ui.page('/')
async def main(client: Client):
    
    @ui.refreshable
    async def chat_messages() -> None:
        for name, text, avatar, stamp in app.storage.user.get('messages', []):
            ui.chat_message(text=text, name=name, stamp=stamp,
                            avatar=avatar, sent=name == 'You', text_html=True)
        
        if app.storage.user.get('thinking', False):
            ui.spinner(size='3rem').classes('self-center')
        await ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)', respond=False)

    async def send() -> None:
        if app.storage.user['guideline'] is None:
            ui.notify('Please select a guideline to chat with!')
            return
        
        message = text.value
        stamp = datetime.utcnow().strftime('%X')
        app.storage.user.get('messages', []).append(('You', text.value, avatar, stamp))
        app.storage.user['thinking'] = True
        text.value = ''
        chat_messages.refresh()

        _llm = create_llm(app.storage.user['guideline'], _levels.index(level_slider.value), _creativity[creativity_slider.value])
        response = await _llm.acall({'question': message, "chat_history": app.storage.user['history']})
        stamp = datetime.utcnow().strftime('%X')

        app.storage.user.get('messages', []).append(
            ('Bot', response['answer'], 'https://robohash.org/assistant?bgset=bg2', stamp))
        app.storage.user['thinking'] = False
        app.storage.user.get('history', []).append((message, response['answer']))
        chat_messages.refresh()

    avatar = f'https://robohash.org/{str(uuid4())}?bgset=bg2'

    anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
    ui.add_head_html(f'<style>{anchor_style}</style>')
    await client.connected()
    
    # for now we just re-intialize the user storage
    # todo: we *may* persist data across sessions and implement chat history
    app.storage.user['guideline'] = None
    app.storage.user['history'] = []
    app.storage.user['messages'] = []
    app.storage.user['thinking'] = False

    app.storage.user['count'] = app.storage.user.get('count', 0) + 1

    print(app.storage.user)

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        await chat_messages()

    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.label('⚕️ Chat with your medical guideline!').classes('text-2xl')

    with ui.dialog() as dialog, ui.card():
        # Get unique "type" values
        data = list_guidelines(True)
        unique_types = set(item["type"] for item in data)

        def _submit(v):  # for ui.tree
            if v in unique_types:
                tree._props['expanded'] = [v]
                tree.update()
            else:
                dialog.submit(
                    [item for item in data if item["title"] == v][0]['dir'])

        ui.label('Chose a guideline to chat with...').classes('text-bold')
        ui.label('Select or search on from this list...')
        ui.select(options=list_guidelines(), with_input=True,
                  on_change=lambda e: dialog.submit(e.value))

        ui.label('Or manually select by name...')
        tree = ui.tree([{'id': t, 'children': [{'id': c['title']}
                                               for c in data if c['type'] == t]} for t in unique_types],
                       label_key='id', on_select=lambda e: _submit(e.value))

    def new_guideline(result):
        print('NEW GUIDELINE')
        print(result)
        if result is None:
            print('Only changed assistent settings')
            return

        print(f'New guideline selected {result}')
        label = list_guidelines()[result]
        app.storage.user['guideline'] = result
        
        print('test')
        print(app.storage.user['messages'])
        print(app.storage.user.get('messages', []))
        print(app.storage.user['messages'])

        app.storage.user['history'] = []
        app.storage.user.get('messages', []).append(
            ('Bot', f'Hello! I am your chat assistant and I have direct access to all the content of <b>{label}</b>. How can I help you? Please ask whatever you want to know.',
             'https://robohash.org/assistant?bgset=bg2', datetime.utcnow().strftime('%X')))
        
        chat_messages.refresh()

        status_label.text = label
        status_div.classes('p-2 bg-green-100')

    async def await_guideline():
        result = await dialog
        new_guideline(result)

    with ui.left_drawer(bottom_corner=True).style('background-color: #d7e3f4'):
        with ui.splitter(horizontal=True).classes('space-y-4') as splitter:
            with splitter.before:
                with ui.element('div').classes('space-y-2'):
                    with ui.column():
                        ui.label('Guideline').classes('text-xl mt-1')
                        ui.button('Pick guideline',
                                  on_click=await_guideline).classes('p-2')
                        ui.button('Random guideline',
                                  on_click=lambda: new_guideline(random.sample(list_guidelines().keys(),
                                                                               1)[0])).classes('p-2 bg-green-100')

                        ui.label('Current guideline').classes(
                            'text-lg mt-2 rounded')
                    with ui.element('div').classes('p-2 bg-red-100 rounded') as status_div:
                        status_label = ui.label(
                            app.storage.user.get('guideline', 'No guideline selected'))
            with splitter.after:
                ui.label('Assistant settings').classes('text-xl mt-1')
                ui.label('Level of conversation').classes('text-lg mt-2')
                level_slider = ui.select(options=['Laymen', 'Intermediate', 'Advanced', 'Expert'],
                                         value='Advanced').on('update:model-value',
                                                              lambda: new_guideline(app.storage.user.get('guideline', 'No guideline selected')))

                ui.label('Creativity of the response').classes('text-lg mt-2')
                creativity_slider = ui.select(options=['Very focused', 'Focused', 'Balanced', 'Creative', 'Very creative'],
                                              value='Creative').on('update:model-value',
                                                                   lambda: new_guideline(app.storage.user.guideline))

    with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            placeholder = 'message'
            text = ui.input(placeholder=placeholder).props('rounded outlined input-class=mx-3') \
                .classes('w-full self-center').on('keydown.enter', send)
        ui.markdown('simple chat app built with [NiceGUI](https://nicegui.io)') \
            .classes('text-xs self-end mr-8 m-[-1em] text-primary')

ui.run(title='Chat with your medical guideline!', favicon='🚀', storage_secret='StyIE3Vkv5YzkOWeKgPt')