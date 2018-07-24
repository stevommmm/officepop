# OfficePOP

Opinionated ActiveSync to POP bridge for restricted exchange environments.

## How
POP Server passes the supplied credentials through to your exchange endpoint. Server is a minimal implementation, may not cover your particular client's commands. Tested using Mutt.

`LIST` shows unread emails only... not all emails in account

`DELE` only marks emails as read, no real deletion.


## Running

Sets up a localhost bound port `:9000` for local use. Simply running `python3 main.py` is enough to get started.


## Requirements

Check [requirements.txt](requirements.txt) for python depends.

Also requires a certificate for the *S* in POPS, generate a self-signed via...
```bash
openssl req -x509 -out localhost.crt -keyout localhost.key \
  -newkey rsa:2048 -nodes -sha256 \
  -subj '/CN=localhost' -extensions EXT -config <( \
   printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")
```

## Muttrc

I use the following for my muttrc. Might work for you too.

```bash
source "~/.mutt/user"

set pop_user="$my_username@$my_domain"
set pop_pass=$my_password
set pop_checkinterval=60
set pop_reconnect=yes
set pop_host="pops://localhost:9000/"
set timeout=60

set from=$pop_user
set use_from=yes
set realname=$my_realname
set smtp_url="smtp://$pop_user@smtp-mail.outlook.com:587"
set smtp_pass=$pop_pass
```
