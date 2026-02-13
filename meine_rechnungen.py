from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from wg.auth import login_required
from wg.db import get_db
from wg.helper import find_all_users, find_all_other_users, find_all_other_users_id, pay_all_debts

import sqlite3

bp = Blueprint('meine_rechnungen', __name__)

@bp.route('/', methods = ['GET','POST'])
@login_required     
def index():
    if request.method == 'POST':
        pay_all_debts(g.user['id'], request.form['submit'])
    
    data = []             #data: userdata-> {username, total, an,von, id}

    other_users = find_all_other_users(g.user['id'])

    for user in other_users:
        total_sum_to_pay = get_total_sum_owed(g.user['id'], user['id'])
        total_sum_to_get = get_total_sum_owed(user['id'], g.user['id'])
        user_data = [
            user['username'],
            round(total_sum_to_get - total_sum_to_pay, 2),
            total_sum_to_pay, total_sum_to_get,
            user['id']
        ]
        data.append(user_data)

    return render_template('meine_rechnungen/index.html', data = data)

@bp.route('/otherRechnungen', methods = ['GET'])
@login_required
def otherRechnungen():
    str_filter = request.args.get("str_filter","") 
    id = g.user['id']
    db = get_db()
    rechnungen = "" #k.a ob ich das brauche, manchmal existiert rechnungen nicht und es kommt zum error
    try:
        rechnungen = db.execute(
        'SELECT amount, title, created, username, rechnung.id, user.id FROM rechnung '
        'JOIN user ON rechnung.schuldiger_id = user.id '  
        'WHERE urheber_id = ? AND title LIKE ?'
        ,
        (id,f"%{str_filter}%",)   # komma um es als tupel zu kennzeichnen
    ).fetchall()

    except sqlite3.Error as e:
        print(f'sqlite.error: {e}')

    return render_template('meine_rechnungen/otherRechnungen.html', rechnungen=rechnungen)

@bp.route('/meineRechnungen', methods = ['GET'])
@login_required
def meineRechnungen():
    str_filter = request.args.get("str_filter","")
    id = g.user['id']
    db = get_db()
    rechnungen = "" #k.a ob ich das brauche, manchmal existiert rechnungen nicht und es kommt zum error
    try:
        rechnungen = db.execute(
            'SELECT amount, title, created, username, rechnung.id, user.id FROM rechnung '
            'JOIN user ON rechnung.urheber_id = user.id '
            'WHERE schuldiger_id = ? AND title LIKE ?',
            (id,f"%{str_filter}%",) # komma um es als tupel zu kennzeichnen
        ).fetchall()

    except sqlite3.Error as e:
        print(f'sqlite.error: {e}')

    return render_template('meine_rechnungen/meineRechnungen.html', rechnungen = rechnungen)

@bp.route('/history', methods = ['GET'])
@login_required
def history():
    id = g.user['id']
    db = get_db()
    offeneRechnungen = ""
    otherRechnungen = ""

    try:
        otherRechnungen = db.execute(
        'SELECT amount, title, created, username, history.id, user.id FROM history '
        'JOIN user ON history.schuldiger_id = user.id '
        'WHERE urheber_id = ?',
        (id,)
        ).fetchall()
    except sqlite3.Error as e:
        print(f'sqlite.error: {e}')

    try:
        offeneRechnungen = db.execute(
        'SELECT amount, title, created, username, history.id, user.id FROM history '
        'JOIN user ON history.urheber_id = user.id ' 
        'WHERE schuldiger_id = ?',
        (id,)
        ).fetchall()
    except sqlite3.Error as e:
        print(f'sqlite.error: {e}')
    

    return render_template('meine_rechnungen/history.html', otherRechnungen = otherRechnungen, offeneRechnungen = offeneRechnungen)

@bp.route('/create', methods = ['GET', 'POST'])
@login_required
def create():
    users = find_all_users()

    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        schuldiger_ids = list(map(int, request.form.getlist('selected_user')))
        error = None

        calculatedIndividualAmount = round(float(amount)/len(schuldiger_ids),2)

        other_users = find_all_other_users_id(g.user['id'])

        if not title:
            error = 'Titel erforderlich'

        if error is not None:
            flash(error)
        else:
            for schuldiger_id in schuldiger_ids:
                if schuldiger_id in other_users:
                    db = get_db()
                    db.execute(                             #TODO amount/menge_ausgewählter_schuldiger
                        'INSERT INTO rechnung (title, amount, urheber_id, schuldiger_id) '
                        'VALUES (?,?,?,?)',
                        (title, calculatedIndividualAmount, g.user['id'], schuldiger_id)
                    )
                    db.commit()
            return redirect(url_for('meine_rechnungen.index')) 
    return render_template('meine_rechnungen/create.html', users = users)

@bp.route('/<int:id>/update', methods = ['GET', 'POST'])
@login_required
def update(id):
    rechnung = get_rechnung(id)

    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']
        error = None

        if not title:
            error = 'Titel erforderlich'
    
        if error is not None:
            flash(error)
    
        else:
            db = get_db()
            db.execute(
                'UPDATE rechnung SET title = ?, amount = ? '
                'WHERE id = ?',
                (title, amount, id)
            )
            db.commit()
            return redirect(url_for('meine_rechnungen.index'))
    return render_template('meine_rechnungen/update.html', rechnung = rechnung)

@bp.route('/<int:id>/delete', methods =  ['POST',])
@login_required
def delete(id):
    get_rechnung(id)
    db = get_db()
    db.execute(
        'DELETE FROM rechnung WHERE id = ?',
        (id,)
    )
    db.commit()
    return redirect(url_for('meine_rechnungen.index'))

def get_rechnung(id, check_urheber=True):
    db = get_db()
    rechnung = db.execute(
        'SELECT r.id, title, amount, created, urheber_id, username '
        'FROM rechnung r JOIN user u ON r.urheber_id = u.id '
        'WHERE r.id = ?'
        ,(id,)
    ).fetchone()

    if rechnung is None:
        abort(404, f'Rechnung id {id} existiert nicht')

    if check_urheber and rechnung['urheber_id'] != g.user['id']:
        abort(403)
    
    return rechnung

def get_total_sum_owed(schuldiger_id, urheber_id):  #should return a float
    db = get_db()

    amount = db.execute(
        'SELECT sum(amount) AS total '
        'FROM rechnung '
        'WHERE schuldiger_id = ? AND urheber_id = ?'
        ,(schuldiger_id, urheber_id)
    ).fetchone()
    
    if amount['total'] == None:
        return 0
    else:
        return round(float(amount['total']),2)
