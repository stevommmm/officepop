#!/usr/bin/env python3
import asyncio
import ssl
import exchangelib as ex
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from email import policy
from hashlib import sha256 as _hash
import logging

def assurelist(obj):
    '''Shortcut wrapper for handling the sometimes None `*_recipients` attributes'''
    if obj == None:
        return []
    return obj


class o365:
    def __init__(self, username, password):
        if isinstance(username, bytes):
            username = username.decode()
        if isinstance(password, bytes):
            password = password.decode()
        self.credentials = ex.Credentials(username, password)
        self.config = ex.Configuration(
            server='outlook.office365.com',
            credentials=self.credentials)
        self.account = ex.Account(
            primary_smtp_address=username,
            config=self.config,
            autodiscover=False,
            access_type=ex.DELEGATE)
        self._inbox_all = []

    @property
    def inbox(self):
        return self.account.inbox

    @property
    def inbox_all(self):
        if not self._inbox_all:
            self._inbox_all = list(self.inbox.filter(is_read=False).order_by('-datetime_received'))
        return self._inbox_all

    @property
    def unread(self):
        return self.inbox.unread_count


async def _handle_connection(reader, writer):
    try:
        await handle_connection(reader, writer)
    except Exception as e:
        logging.warning(e)
        writer.write(b'-ERR Encountered a problem talking to o365\r\n')
        await writer.drain()


async def handle_connection(reader, writer):
    print("Got connection")
    state = {
        'username': None,
        'addr':  writer.get_extra_info('peername')[0],
    }

    def _rwrite(message):
        if not message.endswith('\r\n'):
            message += '\r\n'
        print("{} -->\t{!r}".format(state['addr'], message))
        writer.write(message.encode())

    def _write(fmt, **kwargs):
        line = (fmt + '\r\n').format(**kwargs)
        _rwrite(line)

    _write('+OK POP3 server ready')
    await writer.drain()

    while True:
        bline = await reader.readline()

        if not bline:
            break

        if not bline.startswith(b'PASS'):  # Probs don't print passwords
            print("{} <--\t{!r}".format(state['addr'], bline))

        parts = bline.decode().rstrip().split(' ')
        command = parts[0]
        if len(parts) > 1:
            params = parts[1:]
        else:
            params = []

        if command == 'CAPA':
            _write('+OK Capability list follows')
            _write('USER')
            _write('LOGIN-DELAY 900')
            _write('EXPIRE NEVER')
            _write('UIDL')
            _write('TOP')
            _write('.')
        elif command == 'USER':
            state['username'] = params[0]
            _write('+OK')
        elif command == 'PASS':
            if state['username']:
                try:
                    state['o365'] = o365(state['username'], params[0])
                    _write('+OK')
                except Exception as e:
                    _write('-ERR o365 bounced us')
            else:
                _write('-ERR Who are you?')
        elif command == 'NOOP':
            _write('+OK')
        elif command == 'QUIT':
            _write('+OK')
            await writer.drain()
            break

        # Are we authenticated?
        if not 'o365' in state:
            continue

        if command == 'STAT':
            _write('+OK {count}', count=state['o365'].unread)
        elif command == 'RETR':
            omsg = state['o365'].inbox_all[int(params[0]) - 1]
            obody = omsg.text_body if omsg.text_body != None else omsg.body
            obody = obody if obody != None else ''
            message = EmailMessage(policy=policy.default.clone(linesep='\r\n', mangle_from_=True)) # Use /r/n lin endings
            message['message-id'] = _hash(obody.encode()).hexdigest()
            message['to'] = ', '.join([formataddr((x.name, x.email_address)) for x in assurelist(omsg.to_recipients)])
            message['cc'] = ', '.join([formataddr((x.name, x.email_address)) for x in assurelist(omsg.cc_recipients)])
            message['bcc'] = ', '.join([formataddr((x.name, x.email_address)) for x in assurelist(omsg.bcc_recipients)])
            message['from'] = formataddr((omsg.sender.name, omsg.sender.email_address))
            if omsg.reply_to:
                message['reply-to'] = formataddr((omsg.reply_to.name, omsg.reply_to.email_address))
            message['date'] = formatdate(omsg.datetime_received.timestamp(), localtime=True)
            message['subject'] = omsg.subject

            message.set_content(obody)

            # handle all attachments
            for attachment in omsg.attachments:
                maintype, subtype = attachment.content_type.split('/', 1)
                message.add_attachment(
                    attachment.content,
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment.name)

            _write('+OK message follows')
            _rwrite(message.as_string().replace('\r\n.', '\r\n..'))  # be sure to byte stuff the termination character
            _write('.')
        elif command == 'DELE':
            oid = int(params[0])
            msg = state['o365'].inbox_all[oid - 1]
            if isinstance(msg, ex.items.MeetingRequest):
                if msg.meeting_request_type != 'InformationalUpdate':
                    if msg.conflicting_meeting_count > 0:
                        msg.accept()
                    else:
                        msg.tentatively_accept(body="Meeting conflict, will review")
            msg.is_read = True
            msg.save()
            _write('+OK message {oid} deleted', oid=oid)

        await writer.drain()

    writer.close()
    print('Server client closed for {}'.format(state['addr']))


if __name__ == '__main__':
    sc = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sc.load_cert_chain('/var/run/secrets/server.crt', '/var/run/secrets/server.key')

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(_handle_connection, '0.0.0.0', 9000, ssl=sc, loop=loop)
    server = loop.run_until_complete(coro)

    print('Serving on {}'.format(server.sockets[0].getsockname()))
    loop.run_forever()
