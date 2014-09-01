#!/user/bin/env python2.7

# This all could be replaced by logger but this lightweight option
# seemed more controllable.

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Logger(object):
    """Logger class handles all writing to log files."""
    error_msgs = {
                   0: "A problem has occurred.",
                   1: "Policy Accounting was given an unknown policy_id",
                   2: "Payment attempt made on a policy in cancel pending"
                 } 

    _instance = None

    def __init__(self):
        """Creates a logger class."""
        self.active = True
        self.pw_hash = generate_password_hash("iws") # just trying to keep out most normal users
        

        
    def __call__(self):
        """Should make logger a singleton class"""
        return self


    def log(self, error_msg, level = "Debug", policy_id = "X"):
        """Logs the error message with level and policy_id"""
        if self.active:
            with open("Logs/policy_id_" + str(policy_id) + ".log", 'a') as inp:
                inp.write("[%s] %s Policy ID: %s\n" % (level, str(datetime.now()), policy_id ))
                inp.write(error_msg + "\n")


    def log_error(self, error_num = 0, policy_id = "X"):
        """Writes error message associated with error num to logs."""
        # find error msg and then log it
        if Logger.error_msgs.has_key(error_num):
            error_msg = Logger.error_msgs[error_num]
        else:
            error_msg = "Unknown error num: " + error_num

        self.log(error_msg, "Error", policy_id);
        print "Error has occurred and has been logged."


    def on(self):
        """Turn logger on so it will write to logs."""
        active = True


    def off(self):
        """Turn logger off so it will not write to logs."""
        active = False

    
    def clear_logs(self, password):
        """Clears all logs in logs file"""
        if check_password_hash(self.pw_hash, password):
            import os
            for the_file in os.listdir("Logs"):
                file_path = os.path.join("Logs", the_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception, e:
                    print e
