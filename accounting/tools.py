#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from logger import Logger

"""
#######################################################
This is the base code for the intern project.

If you have any questions, please contact Amanda at:
    amanda@britecore.com
#######################################################
"""

logger = Logger()

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        """Constructs a object linking policies with invoices.
  
        policy_id -- Primary key of policies table
        """
        policy_query = Policy.query.filter_by(id=policy_id)
        if policy_query.count() == 0:
            #create new policy
            print "Policy does not exist"
            logger.log_error(1, policy_id)  
        else:
            self.policy = policy_query.one() 
            if not self.policy.invoices:
                self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        """Return the current account balance based on invocies minus payments.

        date_cursor -- Date object (defaults to current date)   
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()

        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        """Inserts a payment into the database.

        contact_id -- primary key of contacts
        date_cursor -- Date object (defaults to current date) 
        amount -- decimal number (default 0)
        """
        contact = Contact.query.filter_by(id=contact_id).one()
        if contact.role != "Agent" and self.evaluate_cancellation_pending_due_to_non_pay(date_cursor):
            logger.log_error(2, self.policy.id)
            print "Payment could not be made because account is in cancel pending, please contact your agent"
            return False

        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id and self.policy.named_insured: 
            contact_id = self.policy.named_insured

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.due_date <= date_cursor)\
                                .order_by(Invoice.due_date)\
                                .all()

        for invoice in invoices:
            if self.return_account_balance(invoice.due_date) > 0:
                return True

        return False

    def evaluate_cancel(self, date_cursor=None):
        """Returns true if a policy should be canceled.

        date_cursor -- Date object (defaults to current date)
        """
        self.policy.status = "Active"
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                self.policy.status = "Canceled"
                self.policy.effective_date = invoice.cancel_date
                db.session.commit()
                return True

        db.session.commit()
        return False


    def make_invoices(self, end_date_cursor = None):
        """Produces next year's worth of invoices."""
        invoices = []
        if not end_date_cursor:
            if self.policy:
                end_date_cursor = self.policy.effective_date + relativedelta(days=365)
            else:
                end_date_cursor = datetime.now().date + relativedelta(days=365)

        for invoice in self.policy.invoices:
            if not invoice.deleted:
                db.session.delete(invoice)
            else:
                invoices.append(invoice)
        
        logger.log("New invoices are being made, invoices for this policy will be have a different invoice_id",
                   "Info",
                   self.policy.id);

        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}
        billing_to_months = {'Annual': 12, 'Two-Pay': 6, 'Quarterly': 3, 'Monthly': 1}

        # create the first invoice
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        # find the months in the billing period
        if billing_to_months.has_key(self.policy.billing_schedule):
            months_in_billing_period = billing_to_months.get(self.policy.billing_schedule)
        else:
            logger.log("Client tried using %s billing schedule" % (self.policy.billing_schedule), 
                       "Info",
                       self.policy.id)
            print "You have chosen a bad billing schedule."

        del billing_schedules["Annual"] # leave out annual from here to simplify
        if self.policy.billing_schedule in billing_schedules.keys(): 
            # find amount of months between end_date_cursor and self.policy.effective_date
            months_left = (end_date_cursor - self.policy.effective_date).days / 30

            invoices_needed = int(months_left / billing_to_months.get(self.policy.billing_schedule))
            first_invoice.amount_due = first_invoice.amount_due / invoices_needed
            
            # create the correct amount of invoices based on variables above
            for i in range(1, invoices_needed):
                months_after_eff_date = i * months_in_billing_period
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / invoices_needed)
                invoices.append(invoice)

        for invoice in invoices:
            db.session.add(invoice)

        db.session.commit()
        self.policy.invoices = invoices

    def change_billing_schedule(self, new_billing_schedule, date_cursor=None):
        """Changes the billing schedule of the current policy"""
        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}
        if self.policy.billing_schedule not in billing_schedules.keys(): 
            logger.log("Client tried using %s billing schedule" % (self.policy.billing_schedule), 
                       "Info",
                       self.policy.id)
            print "You have chosen a bad billing schedule."
            return
            
        if not date_cursor:
            date_cursor = datetime.now().date()

        new_balance = self.return_account_balance(self.policy.effective_date + relativedelta(days=365))

        # delete all old invoices
        for each_invoice in self.policy.invoices: 
            if self.return_account_balance(each_invoice.due_date) == 0:
                each_invoice.deleted = True
            else:
                db.session.delete(each_invoice)

        # change billing schedule and effective date of policy
        self.policy.billing_schedule = new_billing_schedule
        old_effective_date = self.policy.effective_date
        self.policy.effective_date = date_cursor
        self.policy.annual_premium = new_balance
        
        # call make_invoices to create new invoices
        self.make_invoices(self.policy.effective_date + relativedelta(days=365))

        db.session.commit()

      

################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    logger.off()
    db.drop_all()
    db.create_all()
    insert_data()
    logger.on()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

