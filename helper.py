from wg.db import get_db

def get_id(obj):
    return obj['id']

def find_all_users():
    db = get_db()

    users = db.execute(
        'SELECT * FROM user'
    ).fetchall()

    return users
#TODO find_all_users_that_are_not_me

def find_all_other_users(id):
    db = get_db()

    return db.execute(
        'SELECT * FROM user '
        'WHERE id != ?'
        ,(id,)
    )

def find_all_other_users_id(id):
    db = get_db()

    other_users =  db.execute(
        'SELECT id FROM user '
        'WHERE id != ?'
        ,(id,)
    )

    return list(map(get_id, other_users))
    
    

#pay all debts to user with id, store all rechnungen in history and remove them from rechnungen
def pay_all_debts(uid, sid):
    db = get_db()
    db.execute(
        'INSERT INTO history (amount, title, urheber_id, schuldiger_id)'
        'SELECT amount, title, urheber_id, schuldiger_id FROM rechnung '
        'WHERE urheber_id = ? AND schuldiger_id = ?'
        ,(uid, sid)
    )
    
    db.execute(  
        'DELETE FROM rechnung '
        'WHERE urheber_id = ? AND schuldiger_id = ? '
        ,(uid, sid)
    )
    db.commit()