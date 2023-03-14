'''
Get the title of a target web page.

To use this example, start Chrome (or any other browser that supports CDP) with
the option `--remote-debugging-port=9000`. The URL that Chrome is listening on
is displayed in the terminal after Chrome starts up.

Then run this script with the Chrome URL as the first argument and the target
website URL as the second argument:

$ python examples/get_title.py \
    ws://localhost:9000/devtools/browser/facfb2295-... \
    https://www.hyperiongray.com
'''
import logging
import os
import sys
import argparse
import subprocess
import time
import trio
from trio_cdp import open_cdp, dom, page, target


log_level = os.environ.get('LOG_LEVEL', 'info').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger('get_title')
logging.getLogger('trio-websocket').setLevel(logging.WARNING)
chat_gpt_url = 'https://chat.openai.com'

async def Connect(url):
    logger.info('Connecting to browser: %s', url)
    async with open_cdp(url) as conn:
        logger.info('Listing targets')
        targets = await target.get_targets()

        for t in targets:
            if (t.type_ == 'page' and
                not t.url.startswith('devtools://') and
                not t.attached):
                target_id = t.target_id
                break

        logger.info('Attaching to target id=%s', target_id)
        async with conn.open_session(target_id) as session:

            logger.info('Navigating to %s', chat_gpt_url)
            await page.enable()
            async with session.wait_for(page.LoadEventFired):
                await page.navigate(chat_gpt_url)

            logger.info('Extracting page title')
            while True:
                try:
                    root_node = await dom.get_document()
                    title_node_id = await dom.query_selector(root_node.node_id, 'title')
                    title = await dom.get_outer_html(title_node_id)
                    if(title=="<title>New chat</title>"):
                        print("Logged in successfully")
                        break
                except:
                    print("Waiting for Chat GPT login")
                    time.sleep(5)
        return session

def start_chat_session(debugging_port):
    cmd = f"chromium --remote-debugging-port={debugging_port}"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # extract the GUID from the output
    while True:
        stderr = process.stderr.readline().decode().strip()
        if stderr.startswith("DevTools listening on ws://127.0.0.1:" + str(debugging_port) + "/devtools/browser/"):
            logger.info(stderr)
            guid_start = stderr.find("ws://127.0.0.1:" + str(debugging_port) + "/devtools/browser/") + len("ws://127.0.0.1:" + str(debugging_port) + "/devtools/browser/")
            guid_end = stderr.find("\n", guid_start)
            guid = stderr[guid_start:guid_end]
            break
    url = stderr.replace("DevTools listening on ","")
    trio.run(Connect,url, restrict_keyboard_interrupt_to_checkpoints=True)

start_chat_session(9000)