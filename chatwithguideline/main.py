#!/usr/bin/env python3
import json, asyncio, time
import random
from datetime import datetime
from dotenv import load_dotenv
from nicegui import Client, ui, app
from typing import List, Tuple
from uuid import uuid4

from llm import create_llm
from constants import (welcome_message, new_guideline_message, list_guidelines,
                       format_bot_message, llm_creativity, llm_levels)
from langchain.callbacks.base import BaseCallbackHandler, AsyncCallbackHandler

load_dotenv()


@ui.page('/')
async def main(client: Client):
    class StreamHandler(AsyncCallbackHandler):
        async def on_llm_new_token(self, token: str, **kwargs) -> None:
            app.storage.user['messages'][-1]['text'] += token	
            chat_messages.refresh()

    async def delayed_message(msg_dict):
        app.storage.user.get('messages', []).append({
            "text": "",
            "name": msg_dict['name'],
            "avatar":  msg_dict['avatar'],   
            "stamp":  msg_dict['stamp']
        })

        for letter in msg_dict['text'].split(' '):
            app.storage.user['messages'][-1]['text'] += f' {letter} '
            chat_messages.refresh()
            await asyncio.sleep(0.1)
    
    @ui.refreshable
    async def chat_messages() -> None:
        for msg_dict in app.storage.user.get('messages', []):
            ui.chat_message(text=msg_dict['text'], 
                            name=msg_dict['name'], 
                            stamp=msg_dict['stamp'],
                            avatar=msg_dict['avatar'], 
                            sent=msg_dict['name'] == 'You', 
                            text_html=True).classes('font-sans')
        
        if app.storage.user.get('thinking', False):
            ui.spinner(size='3rem').classes('self-center')
        await ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)', respond=False)

    async def send() -> None:
        if app.storage.user['guideline'] is None:
            ui.notify('Please select a guideline to chat with!')
            return
        
        message = text.value
        stamp = datetime.utcnow().strftime('%X')
        app.storage.user.get('messages', []).append({"name": 'You', "text": text.value, "avatar": avatar, "stamp": stamp})
        text.value = ''
        app.storage.user['thinking'] = False
        chat_messages.refresh()

        app.storage.user.get('messages', []).append(format_bot_message(''))

        _llm = create_llm(app.storage.user['guideline'], 
                          llm_levels.index(level_slider.value), 
                          llm_creativity[creativity_slider.value],
                          StreamHandler())
        
        result = _llm.acall(
                {"question": message, "chat_history": app.storage.user['history']}
        )
        await result

        app.storage.user.get('history', 
                             []).append((message, app.storage.user['messages'][-1]['text']))

    avatar = f'https://robohash.org/{str(uuid4())}?bgset=bg2'

    anchor_style = r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}'
    ui.add_head_html(f'<style>{anchor_style}</style>')
    await client.connected()
    
    # for now we just re-intialize the user storage
    # todo: we *may* persist data across sessions and implement chat history
    app.storage.user['guideline'] = None
    app.storage.user['history'] = []
    app.storage.user['messages'] : list[dict] = []
    app.storage.user['thinking'] = False

    asyncio.ensure_future(delayed_message(format_bot_message(welcome_message)))

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        await chat_messages()

    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.label('⚕️ Chat with your medical guideline!').classes('text-2xl')

    with ui.dialog() as dialog, ui.card():
        # Get unique "type" values
        data = list_guidelines(True)
        unique_types = sorted(set(item["type"].strip() for item in data))

        def _submit(v):  # for ui.tree
            if v in unique_types:
                tree._props['expanded'] = [v]
                tree.update()
            else:
                dialog.submit(
                    [item for item in data if item["title"] == v][0]['dir'])

        ui.label('Choose a guideline to chat with...').classes('text-bold')
        ui.label('Select or search on from this list...')
        ui.select(options=list_guidelines(), with_input=True,
                  on_change=lambda e: dialog.submit(e.value))

        ui.label('Or manually select by name...')
        tree = ui.tree([{'id': t, 'children': [{'id': c['title']}
                                               for c in data if c['type'].strip() == t]} for t in unique_types],
                       label_key='id', on_select=lambda e: _submit(e.value))

    async def new_guideline(result):
        if result is None:
            return

        label = list_guidelines()[result]
        app.storage.user['guideline'] = result

        _msg = new_guideline_message.format(label=label,
                                           level=level_slider.value,
                                           creativity=creativity_slider.value)
        asyncio.ensure_future(delayed_message(format_bot_message(_msg)))    
        status_label.text = label
        status_div.classes('p-2 bg-green-100')

    async def await_guideline():
        result = await dialog
        await new_guideline(result)

    async def await_random_guideline():
        await new_guideline(random.sample(list_guidelines().keys(), 1)[0])

    with ui.left_drawer(bottom_corner=True).style('background-color: #d7e3f4'):
        with ui.splitter(horizontal=True).classes('space-y-4') as splitter:
            with splitter.before:
                with ui.element('div').classes('space-y-2'):
                    with ui.column():
                        ui.label('Guideline').classes('text-xl mt-1')
                        ui.button('Pick guideline',
                                  on_click=await_guideline).classes('p-2')
                        ui.button('Random guideline',
                                  on_click=await_random_guideline).classes('p-2 bg-green-100')

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

import argparse, os
parser = argparse.ArgumentParser()
parser.add_argument(
    "--trace", help="employ langchain tracing", action="store_true")
args = parser.parse_args()

if args.trace:
    import subprocess
    os.environ["LANGCHAIN_TRACING"] = "true"
    subprocess.run(["langchain", "plus", "start"])

ui.run(title='Chat with your medical guideline!',
           favicon='🚀', storage_secret='StyIE3Vkv5YzkOWeKgPt')