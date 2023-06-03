from nicegui import ui
import json


def list_guidelines(with_specialty=False) -> dict:
    with open('embeddings/metadata.json', 'r') as f:
        if with_specialty:
            return json.load(f)
        else:
            return {x['dir']: x['title'] for x in json.load(f)}


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


async def show():
    result = await dialog
    ui.notify(f'You chose {result}')

ui.button('Await a dialog', on_click=show)

ui.run()
