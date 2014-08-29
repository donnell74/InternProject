#!/user/bin/env python2.7

from datetime import datetime

class Logger(object):
    error_msgs = {
                   0: "A problem has occurred.",
                   1: 
                 } 

    def __init__(self):
        self.active = True

    def log(self, level = "Debug", error_msg, policy_id = "X"):
        if self.active:
            with open("Logs/policy_id_" + str(policy_id) + ".log", 'a') as inp:
                inp.write("[%s] %s Policy ID: %s\n" % (level, str(datetime.now()), policy_id ))
                inp.write(error_msg + "\n")

            print "Error has occurred and has been logged."

    def log_error(self, error_num = 0, policy_id = "X"):
        if Logger.error_msgs.has_key(error_num):
            error_msg = Logger.error_msgs[error_num]
        else:
            error_msg = "Unknown error num: " + error_num

        self.log("Error", error_msg, policy_id);

    def on(self):
        active = True


    def off(self):
        active = False
