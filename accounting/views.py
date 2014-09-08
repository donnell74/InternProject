# You will probably need more methods from flask but this one is a good start.
from flask import *

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy, Payment

from tools import *

from datetime import date, datetime
import os

# Routing for the server.
@app.route("/view/")
@app.route("/view/<policy_id>")
@app.route("/view/<policy_id>/")
@app.route("/view/<policy_id>/<year>/<month>/<day>")
def index(policy_id=None, year=None, month=None, day=None):
    url_for('static', filename='style.css')
    if policy_id == None:
        return "Unknown Policy Id"

    if year == None:
        date_cursor = datetime.now().date()
    else:
        date_cursor = date(int(year), int(month), int(day))

    pa = PolicyAccounting(policy_id)
    pa.evaluate_cancel(date_cursor)

    if pa.policy.agent:
        pa.policy.agent = Contact.query.filter_by(id=pa.policy.agent).one().name

    if pa.policy.named_insured:
        pa.policy.named_insured = Contact.query.filter_by(id=pa.policy.named_insured).one().name

    pa.policy.payments = Payment.query.filter_by(policy_id=pa.policy.id).all()
    for payment in pa.policy.payments:
        payment.contact = Contact.query.filter_by(id=payment.contact_id).one().name
    
    pa.policy.amount_due = pa.return_account_balance(date_cursor) 
    
    return render_template('view.html', policy=pa.policy)
