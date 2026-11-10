from escalation import check_escalation

assert check_escalation("I want to talk to a human")["escalate"] is True
assert check_escalation("Your service is terrible")["escalate"] is True
assert check_escalation("Can you advise me about investing?")["escalate"] is True
assert check_escalation("What are your business hours?")["escalate"] is False

print("TEST PASSED")
print("Human requests, complaints, and investment questions are flagged.")