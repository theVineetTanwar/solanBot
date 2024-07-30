
    
def get_public_ip():
    response = requests.get("https://api.ipify.org")
    return response.text

def setIpAddressInMongo():
    atlas_group_id = ""
    atlas_api_key_public = ""
    atlas_api_key_private = ""
    ip = get_public_ip()
    print('-ip:',ip)
    
    resp = requests.post(
        "https://cloud.mongodb.com/api/atlas/v1.0/groups/{atlas_group_id}/accessList".format(atlas_group_id=atlas_group_id),
        auth=HTTPDigestAuth(atlas_api_key_public, atlas_api_key_private),
        json=[{'ipAddress': ip, 'comment': 'From PythonAnywhere'}] 
    )
    if resp.status_code in (200, 201):
        # Wait for a short period to allow the IP address change to propagate
        # time.sleep(30)
        # Connect to MongoDB
        client = MongoClient(dbURI)
        db = client['db']
        global wallet_collection
        wallet_collection = db['wallets']
        print('-wallet',wallet_collection)
        
        all_users = []
        try:
            for user_dict in wallet_collection.find():
                all_users.append(UserModel(**user_dict))
        except Exception as e:
            print(f'Error getting all users: {e}')
        
        for user in all_users:
            print('u',user)
            
    else:
        print(
            "MongoDB Atlas accessList request problem: status code was {status_code}, content was {content}".format(
                status_code=resp.status_code, content=resp.content
            ),
            flush=True
        )
        