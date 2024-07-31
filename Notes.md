# setup python environment
- create an environment
  ```cmd
   python -m venv <environment name>
  ```
- activate/start an environment ( run the ffollowing command from `cmd`)
  ```cmd
   <environment name>\Scripts\activate
  ```

- clone a (python)repo and than setup
  ```cmd
  python -m ensurepip --upgrade # to upgrade pip
  pip3 install -r  ./requirements.txt # to install all dependency
  ````


// got on message sent;;; messageHandler
Update(
  message=Message(channel_chat_created=False, chat=Chat(first_name='D', id=915114249, last_name='G', type=<ChatType.PRIVATE>, username='kygoskyrus'), date=datetime.datetime(2024, 7, 17, 9, 12, 30, tzinfo=<UTC>), delete_chat_photo=False, from_user=User(first_name='D', id=915114249, is_bot=False, language_code='en', last_name='G', username='kygoskyrus'), group_chat_created=False, message_id=26, supergroup_chat_created=False, text='Hell'), 
  update_id=638557823
  )




-update Update(callback_query=CallbackQuery(chat_instance='-4421070697837062638', data='generate_wallet', from_user=User(first_name='D', id=915114249, is_bot=False, languag
e_code='en', last_name='G', username='kygoskyrus'), id='3930385775547828245', message=Message(channel_chat_created=False, chat=Chat(first_name='D', id=915114249, last_name=
'G', type=<ChatType.PRIVATE>, username='kygoskyrus'), date=datetime.datetime(2024, 7, 18, 8, 43, 28, tzinfo=<UTC>), delete_chat_photo=False, edit_date=datetime.datetime(202
4, 7, 18, 8, 43, 33, tzinfo=<UTC>), from_user=User(first_name='Crypto bot', id=7315336925, is_bot=True, username='crypto737263_bot'), group_chat_created=False, message_id=6
8, reply_markup=InlineKeyboardMarkup(inline_keyboard=((InlineKeyboardButton(callback_data='generate_wallet', text='Generate Wallet'), InlineKeyboardButton(callback_data='ex
port_private_key', text='Export Private Key')), (InlineKeyboardButton(callback_data='withdraw_sol', text='Withdraw SOL'), InlineKeyboardButton(callback_data='back_to_main',
 text='Back')))), supergroup_chat_created=False, text='Manage Wallet')), update_id=638557861)

-query CallbackQuery(chat_instance='-4421070697837062638', data='generate_wallet', from_user=User(first_name='D', id=915114249, is_bot=False, language_code='en', last_name='G', username='kygoskyrus'), id='3930385775547828245', message=Message(channel_chat_created=False, chat=Chat(first_name='D', id=915114249, last_name='G', type=<ChatType.PRIVATE>, username='kygoskyrus'), date=datetime.datetime(2024, 7, 18, 8, 43, 28, tzinfo=<UTC>), delete_chat_photo=False, edit_date=datetime.datetime(2024, 7, 18, 8, 43, 33, tzinfo=<UTC>), from_user=User(first_name='Crypto bot', id=7315336925, is_bot=True, username='crypto737263_bot'), group_chat_created=False, message_id=68, reply_markup=InlineKeyboardMarkup(inline_keyboard=((InlineKeyboardButton(callback_data='generate_wallet', text='Generate Wallet'), InlineKeyboardButton(callback_data='export_private_key', text='Export Private Key')), (InlineKeyboardButton(callback_data='withdraw_sol', text='Withdraw SOL'), InlineKeyboardButton(callback_data='back_to_main', text='Back')))), supergroup_chat_created=False, text='Manage Wallet'))




<!-- sol bal by shyft API-->
- {"success":true,"message":"Balance fetched successfully","result":{"balance":0}}

<!-- by CLIENT -->
{ context: RpcResponseContext { slot: 315261273, api_version: Some("1.18.20") }, value: 5000002000 }


project-id::6698ddfdbb059101114a9446
public key : fptqslnn

private key: c589e434-c8ed-471b-82fb-d79a54a218e3


dbURI = "mongodb+srv://vineet:Zf2eJGOfvbHVwPuL@testcluster.yqndany.mongodb.net/?retryWrites=true&w=majority&appName=testCluster" 
TOKEN = "7315336925:AAHu6_EX-pmpmxl8DmjO8IBHKwAFl_IhQlM"
SHYFT_API_KEY = "GlJ737ibT8z26T3f"




# sender = Keypair.from_base58_string("3i9fUTcRqNJdVZhcnTCWvJMBgBVG2MAXF7VyXTiYGpuA9KQaED1284KnSxeqtTLfD58tALNwuvjc3BKcv6CPTz5C")
# senderPubKey = Pubkey.from_string("8cfh68gHXenoPEZcEe8HtzdDKcWuR48CS4Wfn3zjdp3Q")
# receiver = Pubkey.from_string("7NWwYNKJpE8qo4rbWuCnExHXdNMwqVhp2s2YB5973tfM")
# amount = 1000


{
    "_id" : ObjectId("66a0d79a251bff873b4eed54"),
    "userId" : NumberInt(1740943720),
    "privateKey" : "b'\\x87\\x85\\x07\\xc1\\xc6)\\xc4\\xa5\\x87\\x90\\xad\\xab\\xc7P^\\xc6\\x19\\xc92F\\x1c\\xceDu\\x9bf\\x89\\x84\\x86\\xb7\\x92g'",
    "publicKey" : "8cfh68gHXenoPEZcEe8HtzdDKcWuR48CS4Wfn3zjdp3Q",
    "keypair" : "3i9fUTcRqNJdVZhcnTCWvJMBgBVG2MAXF7VyXTiYGpuA9KQaED1284KnSxeqtTLfD58tALNwuvjc3BKcv6CPTz5C"
}

{
    "_id" : ObjectId("66a7452aa6a1b7f295e856d9"),
    "userId" : NumberInt(915114249),
    "privateKey" : "SSIg7+QFTUA16QymJgRFdDE0j4BWaYAhBBhR1WrZjrE=",
    "publicKey" : "7NWwYNKJpE8qo4rbWuCnExHXdNMwqVhp2s2YB5973tfM",
    "keypair" : "2Tojm2pUxXe4KPfnbzNwKWXb5jjT7J91FHfZ9qKwyx8MaSEiwRztSFuf9oV69BsGj7j5g9H6dPzhfe8u8Tspzdwh"
}