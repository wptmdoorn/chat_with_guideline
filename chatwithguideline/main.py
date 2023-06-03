#!/usr/bin/env python3
import json
from datetime import datetime
from dotenv import load_dotenv
from nicegui import Client, ui
from typing import List, Tuple
from uuid import uuid4

from llm import create_llm


load_dotenv()

selected_guideline = None
llm = None
chat_history = []
messages: List[Tuple[str, str, str, str]] = []
thinking: bool = False


def list_guidelines(with_specialty=False) -> dict:
    with open('embeddings/metadata.json', 'r') as f:
        if with_specialty:
            return json.load(f)
        else:
            return {x['dir']: x['title'] for x in json.load(f)}


@ui.refreshable
async def chat_messages() -> None:
    for name, text, avatar, stamp in messages:
        ui.chat_message(text=text, name=name, stamp=stamp,
                        avatar=avatar, sent=name == 'You', text_html=True)
    if thinking:
        ui.spinner(size='3rem').classes('self-center')
    await ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)', respond=False)


@ui.page('/')
async def main(client: Client):
    async def send() -> None:
        if selected_guideline is None:
            ui.notify('Please select a guideline to chat with!')
            return

        global thinking
        message = text.value
        stamp = datetime.utcnow().strftime('%X')
        messages.append(('You', text.value, avatar, stamp))
        thinking = True
        text.value = ''
        chat_messages.refresh()

        response = await llm.acall({'question': message, "chat_history": chat_history})
        print(response)
        stamp = datetime.utcnow().strftime('%X')

        messages.append(
            ('Bot', response['answer'], 'https://robohash.org/assistant?bgset=bg2', stamp))
        thinking = False
        chat_history.append((message, response['answer']))
        chat_messages.refresh()

    avatar = f'https://robohash.org/{str(uuid4())}?bgset=bg2'

    anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
    ui.add_head_html(f'<style>{anchor_style}</style>')
    await client.connected()

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        await chat_messages()

    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.label('Talk with your medical guideline!').classes('text-2xl')

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

    async def new_guideline(random=True):
        if random:
            result = random.sample(list_guidelines().keys(), 1)
        else:
            result = await dialog
        print(f'New guideline selected {result}')
        label = list_guidelines()[result]

        global messages, llm, chat_history, selected_guideline

        selected_guideline = result
        llm = create_llm(result)
        messages = []
        chat_history = []
        messages.append(
            ('Bot', f'Hello! I am your chat assistant and I have direct access to all the content of <b>{label}</b>. How can I help you? Please ask whatever you want to know.',
             'https://robohash.org/assistant?bgset=bg2', datetime.utcnow().strftime('%X')))

        chat_messages.refresh()

        status_label.text = label
        status_div.classes('p-2 bg-green-100')

    with ui.left_drawer(bottom_corner=True).style('background-color: #d7e3f4'):
        with ui.splitter(horizontal=True).classes('space-y-4') as splitter:
            with splitter.before:
                with ui.element('div').classes('space-y-2'):
                    ui.label('Guideline').classes('text-xl mt-1')
                    ui.button('Pick guideline',
                              on_click=lambda e: new_guideline(False)).classes('p-2')
                    ui.button('Random guideline',
                              on_click=lambda e: new_guideline(True)).classes('p-2 bg-green-100')

                    ui.label('Current guideline').classes('text-lg mt-2')
                    with ui.element('div').classes('p-2 bg-red-100') as status_div:
                        status_label = ui.label(
                            selected_guideline or 'No guideline selected')
            with splitter.after:
                ui.label('Settings').classes('text-xl mt-1')
                ui.label('Exploration rate').classes('text-lg mt-2')
                exploration_slider = ui.slider(
                    min=0, max=1, value=0.5, step=0.1)
                ui.label().bind_text_from(exploration_slider, 'value')

                ui.label('Maximum length of response').classes('text-lg mt-2')
                token_slider = ui.slider(
                    min=100, max=4000, value=2000, step=10)
                ui.label().bind_text_from(token_slider, 'value')

    with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            placeholder = 'message'
            text = ui.input(placeholder=placeholder).props('rounded outlined input-class=mx-3') \
                .classes('w-full self-center').on('keydown.enter', send)
        ui.markdown('simple chat app built with [NiceGUI](https://nicegui.io)') \
            .classes('text-xs self-end mr-8 m-[-1em] text-primary')

ui.run(title='Chat with GPT-3 (example)')
